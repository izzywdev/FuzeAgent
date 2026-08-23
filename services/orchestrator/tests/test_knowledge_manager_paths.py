"""
Regression tests for the path-traversal (CWE-22) and SSRF (CWE-918) fixes in
``knowledge_manager.py`` -- the 17 CodeQL alerts (1 critical, 16 high) that were
pre-existing on ``main`` and surfaced by PR #173.

These assert the REJECTIONS specifically. A test that only shows the happy path
still passes against the vulnerable code, which is the whole trap: the point of
this file is that a traversing id, a caller-controlled filename, and a URL
pointing at link-local/loopback/private space are each refused.

Everything here is filesystem/network-free apart from a tmp_path storage root:
``requests.get`` is patched, and hostname resolution is patched where a test
needs a specific address without depending on real DNS.
"""

import os
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point the module-level storage root somewhere harmless BEFORE import: importing
# knowledge_manager instantiates a global KnowledgeManager() which mkdir()s it.
_TEST_ROOT = Path(__file__).resolve().parent / "_km_storage"
os.environ["KNOWLEDGE_STORAGE_PATH"] = str(_TEST_ROOT)

import knowledge_manager as km  # noqa: E402

pytestmark = pytest.mark.unit


@pytest.fixture()
def manager(tmp_path, monkeypatch):
    """A KnowledgeManager rooted in a throwaway tmp dir."""
    monkeypatch.setattr(km, "KNOWLEDGE_STORAGE_PATH", str(tmp_path))
    mgr = km.KnowledgeManager()
    mgr.storage_path = tmp_path
    for sub in ("organizations", "teams", "agents", "temp"):
        (tmp_path / sub).mkdir(exist_ok=True)
    return mgr


# --------------------------------------------------------------------------
# CWE-22 -- scope ids must not be able to leave the storage root
# --------------------------------------------------------------------------

TRAVERSING_IDS = [
    "../../../../etc",
    "..",
    "../evil",
    "a/../../b",
    "/etc/passwd",
    "foo/bar",
    "with space",
    "sneaky\x00null",
    "....//....//etc",
    "%2e%2e%2fetc",
    "x" * 65,  # length cap
]


@pytest.mark.parametrize("bad", TRAVERSING_IDS)
@pytest.mark.parametrize("kind", ["agent_id", "team_id", "organization_id"])
def test_scope_id_traversal_is_rejected(manager, bad, kind):
    """Every scope parameter is rejected, not sanitised, for a traversing value."""
    with pytest.raises(km.UnsafeInputError):
        manager._get_storage_path(**{kind: bad})


@pytest.mark.parametrize("good", ["agent-1", "Team_42", "org-abc123", "a", "x" * 64])
def test_legitimate_scope_ids_still_work(manager, good):
    """The allowlist must not break ordinary ids -- a fix nobody can use is a bug."""
    path = manager._get_storage_path(agent_id=good)
    assert path.is_relative_to(manager.storage_path.resolve())
    assert path.name == good


def test_no_scope_falls_back_to_temp(manager):
    assert manager._get_storage_path().name == "temp"


# --------------------------------------------------------------------------
# CWE-22 -- doc_id reaches a filename and, in delete, a glob feeding unlink()
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad", ["../../etc/passwd", "*", "..", "a/b", "not-a-uuid", "", "?" * 8]
)
def test_doc_id_must_be_a_uuid(bad):
    with pytest.raises(km.UnsafeInputError):
        km._validate_doc_id(bad)


def test_doc_id_accepts_a_real_uuid():
    val = str(uuid.uuid4())
    assert km._validate_doc_id(val) == val


@pytest.mark.asyncio
async def test_delete_document_rejects_traversing_doc_id(manager, tmp_path):
    """The worst path: glob(f'{doc_id}*') + unlink() with a caller-supplied id."""
    victim = tmp_path / "victim.txt"
    victim.write_text("do not delete me")

    # delete_document swallows exceptions and returns False; what matters is that
    # the file survives.
    result = await manager.delete_document("../*", agent_id="agent-1")
    assert result is False
    assert victim.exists(), "traversing doc_id deleted a file outside the scope"


@pytest.mark.asyncio
async def test_get_document_metadata_rejects_traversing_doc_id(manager):
    with pytest.raises(km.UnsafeInputError):
        await manager.get_document_metadata("../../secret", agent_id="agent-1")


# --------------------------------------------------------------------------
# CWE-22 -- the containment backstop itself
# --------------------------------------------------------------------------


def test_ensure_within_allows_the_root_and_children(tmp_path):
    assert km._ensure_within(tmp_path, tmp_path) == tmp_path.resolve()
    assert km._ensure_within(tmp_path, tmp_path / "a" / "b").name == "b"


def test_ensure_within_rejects_escape(tmp_path):
    with pytest.raises(km.UnsafeInputError):
        km._ensure_within(tmp_path, tmp_path / ".." / "outside")


def test_ensure_within_rejects_symlink_escape(tmp_path):
    """Resolving both sides means a symlink inside the root cannot escape it."""
    outside = tmp_path.parent / "outside_target"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")
    with pytest.raises(km.UnsafeInputError):
        km._ensure_within(tmp_path, link / "loot")


# --------------------------------------------------------------------------
# CWE-918 -- SSRF
# --------------------------------------------------------------------------

BLOCKED_URLS = [
    "http://169.254.169.254/latest/meta-data/",  # cloud metadata -- the real prize
    "http://127.0.0.1:8000/admin",
    "http://localhost/",
    "http://[::1]/",
    "http://10.0.0.5/",
    "http://192.168.1.1/",
    "http://172.16.0.1/",
    "http://0.0.0.0/",
]


@pytest.mark.parametrize("url", BLOCKED_URLS)
def test_ssrf_blocks_non_public_targets(url):
    with pytest.raises(km.UnsafeInputError):
        km._validate_public_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "gopher://127.0.0.1:11211/_stats",
        "ftp://internal/",
        "//no-scheme/",
        "http://",
    ],
)
def test_ssrf_blocks_non_http_schemes(url):
    with pytest.raises(km.UnsafeInputError):
        km._validate_public_url(url)


def test_ssrf_allows_a_public_host(monkeypatch):
    monkeypatch.setattr(
        km.socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 80))],
    )
    assert km._validate_public_url("http://example.com/doc") == "http://example.com/doc"


def test_ssrf_redirect_to_metadata_is_blocked(monkeypatch):
    """A guard that only checks the FIRST url is not a guard at all."""
    monkeypatch.setattr(
        km.socket,
        "getaddrinfo",
        lambda host, *a, **k: (
            [(2, 1, 6, "", ("93.184.216.34", 80))]
            if host == "example.com"
            else [(2, 1, 6, "", ("169.254.169.254", 80))]
        ),
    )

    class _Resp:
        is_redirect = True
        is_permanent_redirect = False
        headers = {"Location": "http://169.254.169.254/latest/meta-data/"}

    calls = []

    def _fake_get(url, **kwargs):
        calls.append(url)
        assert kwargs.get("allow_redirects") is False, "must not auto-follow redirects"
        return _Resp()

    monkeypatch.setattr(km.requests, "get", _fake_get)

    with pytest.raises(km.UnsafeInputError):
        km._fetch_url_safely("http://example.com/start")

    assert calls == [
        "http://example.com/start"
    ], "metadata endpoint must not be fetched"


def test_ssrf_redirect_loop_is_bounded(monkeypatch):
    monkeypatch.setattr(
        km.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 80))]
    )

    class _Resp:
        is_redirect = True
        is_permanent_redirect = False
        headers = {"Location": "http://example.com/next"}

    monkeypatch.setattr(km.requests, "get", lambda url, **kw: _Resp())
    with pytest.raises(km.UnsafeInputError):
        km._fetch_url_safely("http://example.com/start")


# --------------------------------------------------------------------------
# CWE-22 -- the caller's filename must never reach the filesystem
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_document_ignores_caller_filename_for_the_path(
    manager, tmp_path, monkeypatch
):
    """The stored name is doc_id + validated extension, never the caller's string."""
    monkeypatch.setattr(km, "MAX_FILE_SIZE", 10_000)

    import io

    meta = await manager.upload_document(
        file_content=io.BytesIO(b"hello"),
        filename="../../../../tmp/pwned.txt",
        agent_id="agent-1",
    )

    scope = tmp_path / "agents" / "agent-1"
    written = list(scope.iterdir())
    # Exactly the content file + the metadata file, both named by doc_id.
    assert {f.name for f in written} == {
        f"{meta.id}.txt",
        f"{meta.id}.metadata.json",
    }
    assert not (tmp_path.parent / "pwned.txt").exists()
    # ...but the original filename survives as inert metadata.
    assert meta.filename == "../../../../tmp/pwned.txt"


@pytest.mark.asyncio
async def test_upload_document_rejects_unsupported_extension(manager):
    import io

    with pytest.raises(ValueError):
        await manager.upload_document(
            file_content=io.BytesIO(b"x"), filename="evil.sh", agent_id="agent-1"
        )


# --------------------------------------------------------------------------
# The (a)-vs-(b) test for the remaining CodeQL alerts.
#
# CodeQL still reports py/path-injection and py/full-ssrf on this file after the
# fix. Three of those alerts sit *inside* `_ensure_within` itself -- the
# sanitizer -- because CodeQL does not model a regex allowlist or
# `Path.resolve()` + `is_relative_to()` as a barrier, so taint still "reaches"
# the guard. The alert count actually went UP (17 -> 19) for exactly that
# reason: `_ensure_within` is a shared confluence point that 21-27 separate
# tainted flows now pass through.
#
# "CodeQL says so" is not evidence of a vulnerability, and "the tests pass" is
# not evidence of its absence. So this test is the discriminator: it drives every
# public entry point with every malicious input class and asserts the only thing
# that actually matters -- that nothing is created, read, or deleted outside the
# storage root. If a future change makes one of those alerts real, this goes red.
# --------------------------------------------------------------------------

_BAD_SCOPES = [
    "../../../../etc",
    "..",
    "/etc",
    "a/../../b",
    "%2e%2e%2f",
    "x" * 65,
    "with space",
    "n\x00ul",
]
_BAD_DOC_IDS = ["../../etc/passwd", "*", "**", "..", "a/b", "not-a-uuid", "?" * 8, ""]
_BAD_FILENAMES = [
    "../../../../tmp/pwned.txt",
    "..%2f..%2fx.txt",
    "a/b/c.txt",
    "\x00.txt",
]


@pytest.mark.asyncio
async def test_no_entry_point_can_touch_anything_outside_the_storage_root(
    manager, tmp_path
):
    """Drive every public method with hostile input; assert zero escapes.

    Deliberately tolerant of *how* each method refuses -- some raise
    UnsafeInputError, some catch it internally and return None/False. What is
    asserted is the outcome on the filesystem, not the shape of the rejection.
    """
    import io

    outside = tmp_path.parent / "outside_canary"
    outside.mkdir(exist_ok=True)
    canary = outside / "canary.txt"
    canary.write_text("SECRET")
    outside_before = sorted(p.name for p in outside.iterdir())

    escape_relative = os.path.relpath(outside, tmp_path / "agents")

    async def _swallow(coro):
        try:
            await coro
        except Exception:
            pass

    for scope in _BAD_SCOPES + [escape_relative]:
        await _swallow(manager.get_documents(agent_id=scope))
        await _swallow(manager.search_documents("q", agent_id=scope))
        await _swallow(
            manager.upload_document(
                file_content=io.BytesIO(b"x"), filename="a.txt", agent_id=scope
            )
        )
        try:
            manager._get_storage_path(agent_id=scope)
        except Exception:
            pass

    for doc_id in _BAD_DOC_IDS:
        await _swallow(manager.get_document_metadata(doc_id, agent_id="agent-1"))
        await _swallow(manager.get_document_content(doc_id, agent_id="agent-1"))
        await _swallow(manager.update_document(doc_id, title="t", agent_id="agent-1"))
        await _swallow(manager.delete_document(doc_id, agent_id="agent-1"))

    for name in _BAD_FILENAMES:
        await _swallow(
            manager.upload_document(
                file_content=io.BytesIO(b"x"), filename=name, agent_id="agent-1"
            )
        )

    # The assertions that decide (a) vs (b).
    assert canary.exists(), "a hostile input deleted a file outside the storage root"
    assert canary.read_text() == "SECRET", "a hostile input overwrote an outside file"
    assert (
        sorted(p.name for p in outside.iterdir()) == outside_before
    ), "a hostile input created a file outside the storage root"

    # Everything that *was* written stayed in-scope and is named by doc_id only.
    written = [p for p in tmp_path.rglob("*") if p.is_file()]
    for path in written:
        assert path.resolve().is_relative_to(
            tmp_path.resolve()
        ), f"{path} escaped the storage root"
        assert (
            path.parent.name == "agent-1"
        ), f"{path} landed outside the caller's scope"


def test_fetch_url_safely_is_the_only_outbound_call():
    """A chokepoint one caller bypasses is not a chokepoint.

    Pins the invariant that no direct `requests.get(url, ...)` is reintroduced
    alongside the guarded helper -- the SSRF alert would then be real.
    """
    import inspect

    source = inspect.getsource(km)
    outbound = [
        line.strip()
        for line in source.splitlines()
        if "requests." in line and not line.strip().startswith("#")
    ]
    assert outbound == [
        "response = requests.get(current, timeout=timeout, allow_redirects=False)"
    ], f"unexpected outbound HTTP call(s) outside _fetch_url_safely: {outbound}"


def test_every_storage_path_goes_through_the_validating_chokepoint():
    """No method may build a scope path without _get_storage_path()."""
    import inspect

    source = inspect.getsource(km.KnowledgeManager)
    # `self.storage_path / ...` is only legitimate inside __init__ (fixed, trusted
    # subdirectory names) and inside _get_storage_path itself (validated + contained).
    offenders = []
    current = None
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("def ") or stripped.startswith("async def "):
            current = (
                stripped.split("(")[0].replace("async def ", "").replace("def ", "")
            )
        if "self.storage_path /" in stripped and current not in (
            "__init__",
            "_get_storage_path",
        ):
            offenders.append((current, stripped))
    assert not offenders, f"scope path built outside the chokepoint: {offenders}"
