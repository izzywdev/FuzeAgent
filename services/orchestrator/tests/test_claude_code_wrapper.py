"""
Unit tests for the Claude Code Wrapper (``claude_code_wrapper.ClaudeCodeWrapper``).

These tests exercise the tool's REAL public surface as shipped:

* construction (a crewai ``BaseTool`` / Pydantic v2 model),
* the tool metadata (``name`` / ``description`` / ``model`` / ``client`` /
  ``args_schema``),
* the synchronous ``_run(...)`` entry point crewai calls, and
* the response parser ``_parse_response(...)``.

Prior revisions of this file asserted against an ``execute({...})`` dict-in /
dict-out method with keys such as ``code_blocks`` / ``task_type`` that this
wrapper has never implemented (it exposes ``_run`` returning a JSON string and
``execute_task_async``). Those tests could never pass against the shipped code;
they are replaced here with tests bound to the actual interface. The Anthropic
SDK client is mocked, so no network or API key is required.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from claude_code_wrapper import ClaudeCodeWrapper

# A response shaped exactly like the ``## Explanation`` / ``### Main Code`` /
# ``### Tests`` / ``## Commit Message`` contract that ``_build_prompt`` asks for
# and ``_parse_response`` consumes.
STRUCTURED_RESPONSE = """
## Explanation
This is a test implementation for calculating the factorial of a number.

## Implementation

### Main Code
```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

### Tests
```python
def test_factorial():
    assert factorial(0) == 1
    assert factorial(5) == 120
```

## Commit Message
feat: add factorial function with recursive implementation
"""


@pytest.mark.unit
class TestClaudeCodeWrapper:
    """Test the ClaudeCodeWrapper tool against its real interface."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Patch the Anthropic SDK class so no real key/network is needed.

        Yields the mocked *client* instance whose ``messages.create`` returns a
        response carrying ``STRUCTURED_RESPONSE`` text.
        """
        with patch("claude_code_wrapper.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = STRUCTURED_RESPONSE
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            yield mock_client

    # -- construction / metadata --------------------------------------------

    def test_wrapper_initialization(self, mock_anthropic_client):
        """The tool constructs and exposes its declared attributes."""
        wrapper = ClaudeCodeWrapper()

        assert wrapper.name == "claude_code"
        # Declared runtime fields must be publicly readable (regression: these
        # used to raise ``"ClaudeCodeWrapper" object has no field "client"``).
        assert wrapper.model == "claude-3-5-sonnet-20241022"
        assert wrapper.client is not None
        assert isinstance(wrapper.description, str) and wrapper.description.strip()
        assert wrapper.args_schema is not None

    def test_constructor_accepts_agent_context(self, mock_anthropic_client):
        """Optional agent/task/workspace context is stored on the instance."""
        wrapper = ClaudeCodeWrapper(
            workspace_path="/tmp/does-not-need-to-exist",  # nosec B108 -- test-only tmp path
            agent_id="agent-123",
            task_id="task-456",
        )

        assert wrapper.workspace_path == "/tmp/does-not-need-to-exist"  # nosec B108 -- test-only tmp path
        assert wrapper.agent_id == "agent-123"
        assert wrapper.task_id == "task-456"
        # repository_context is initialised as a fresh dict per instance.
        assert wrapper.repository_context["iteration_count"] == 0

    # -- _run success path ---------------------------------------------------

    def test_run_generates_files(self, mock_anthropic_client, tmp_path):
        """``_run`` returns a JSON envelope with parsed implementation files."""
        wrapper = ClaudeCodeWrapper(workspace_path=str(tmp_path))

        raw = wrapper._run(
            task="Create a factorial function",
            language="python",
            include_tests=False,
            include_docs=False,
        )
        result = json.loads(raw)

        assert result["status"] == "success"
        impl = [f for f in result["files"] if f["type"] == "implementation"]
        assert impl, "expected an implementation file"
        assert "factorial" in impl[0]["content"]
        assert "factorial" in result["explanation"].lower()

        # The Anthropic client was called with the configured model.
        mock_anthropic_client.messages.create.assert_called_once()
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-5-sonnet-20241022"
        prompt_text = call_kwargs["messages"][0]["content"]
        assert "factorial" in prompt_text.lower()

    def test_run_reports_errors(self, mock_anthropic_client, tmp_path):
        """Exceptions from the API are caught and surfaced as a JSON error."""
        mock_anthropic_client.messages.create.side_effect = RuntimeError("boom")
        wrapper = ClaudeCodeWrapper(workspace_path=str(tmp_path))

        result = json.loads(wrapper._run(task="anything", language="python"))

        assert result["status"] == "error"
        assert "boom" in result["error"]

    # -- _parse_response -----------------------------------------------------

    def test_parse_response_extracts_sections(self, mock_anthropic_client):
        """The parser pulls explanation, commit message and code files out."""
        wrapper = ClaudeCodeWrapper()

        parsed = wrapper._parse_response(
            STRUCTURED_RESPONSE,
            language="python",
            include_tests=True,
            include_docs=False,
        )

        assert (
            parsed["explanation"]
            == "This is a test implementation for calculating the factorial of a number."
        )
        assert (
            parsed["commit_message"]
            == "feat: add factorial function with recursive implementation"
        )

        types = {f["type"] for f in parsed["files"]}
        assert "implementation" in types
        assert "test" in types  # include_tests=True → a test file is emitted
        main = next(f for f in parsed["files"] if f["type"] == "implementation")
        assert main["language"] == "python"
        assert "factorial" in main["content"]
