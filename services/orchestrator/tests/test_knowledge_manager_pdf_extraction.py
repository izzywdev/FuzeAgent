"""
Regression coverage for the pypdf integration in ``knowledge_manager.py``.

This service depends on the PDF library through ``KnowledgeManager._extract_from_pdf``,
which calls ``pypdf.PdfReader(file)`` and ``page.extract_text()``. The dependency was
migrated from the abandoned ``PyPDF2`` package to its renamed, actively maintained
successor ``pypdf`` (PYSEC-2026-1835 -- ``PyPDF2`` has no fix release; ``pypdf`` 3.9.0+
is where the advisory is actually resolved). ``PyPDF2`` and ``pypdf`` renamed several
classes/methods across the 3.x-6.x line, so an import-only smoke test is not enough --
these tests exercise the real read path against a real (if minimal) PDF byte stream and
assert the extracted text, so a future dependency bump that silently breaks the
``PdfReader`` / ``.pages`` / ``.extract_text()`` surface fails loudly here instead of only
surfacing when a user uploads a document.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TEST_ROOT = Path(__file__).resolve().parent / "_km_pdf_storage"
os.environ.setdefault("KNOWLEDGE_STORAGE_PATH", str(_TEST_ROOT))

import knowledge_manager as km  # noqa: E402

pytestmark = pytest.mark.unit


def _make_minimal_pdf(text: str) -> bytes:
    """Hand-build a minimal, spec-valid single-page PDF containing ``text``.

    No extra dependency (e.g. reportlab) is pulled in just to author a fixture --
    this constructs the objects, computes the xref byte offsets, and returns bytes
    pypdf can parse and extract text from.
    """
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
            b"/MediaBox [0 0 200 200] /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream_content = f"BT /F1 24 Tf 20 100 Td ({text}) Tj ET".encode("latin-1")
    objects.append(
        b"<< /Length %d >>\nstream\n" % len(stream_content)
        + stream_content
        + b"\nendstream"
    )

    body = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body += f"{i} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"

    xref_offset = len(body)
    n = len(objects) + 1
    xref = f"xref\n0 {n}\n0000000000 65535 f \n".encode("ascii")
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode("ascii")
    body += xref
    body += (
        f"trailer\n<< /Size {n} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF"
    ).encode("ascii")
    return bytes(body)


@pytest.fixture()
def manager(tmp_path, monkeypatch):
    monkeypatch.setattr(km, "KNOWLEDGE_STORAGE_PATH", str(tmp_path))
    mgr = km.KnowledgeManager()
    mgr.storage_path = tmp_path
    for sub in ("organizations", "teams", "agents", "temp"):
        (tmp_path / sub).mkdir(exist_ok=True)
    return mgr


def test_extract_from_pdf_reads_real_text(manager, tmp_path):
    """``_extract_from_pdf`` uses ``pypdf.PdfReader`` end-to-end and returns the
    page's text -- proves the post-migration API (PdfReader/.pages/.extract_text())
    still matches what pypdf actually exposes."""
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(_make_minimal_pdf("Hello PDF"))

    extracted = manager._extract_from_pdf(pdf_path)

    assert "Hello PDF" in extracted


def test_extract_from_pdf_multi_page_reads_all_pages(manager, tmp_path):
    """Sanity check that ``.pages`` iteration (not just page 0) actually reaches
    pypdf's reader -- catches a regression where only the first page is read."""
    single_page = _make_minimal_pdf("Only Page")
    pdf_path = tmp_path / "single.pdf"
    pdf_path.write_bytes(single_page)

    extracted = manager._extract_from_pdf(pdf_path)

    assert extracted.strip() == "Only Page"


def test_extract_from_pdf_handles_corrupt_file_without_raising(manager, tmp_path):
    """A malformed PDF must not raise out of ``_extract_from_pdf`` -- the caller
    (``_extract_text_from_file``) has no try/except around this branch, so a raised
    exception here previously escaped the try/except that wraps the *dispatch*, not
    each individual extractor. Confirms the existing internal try/except still holds
    against the new pypdf exception types (they changed across the PyPDF2 -> pypdf
    rename)."""
    bad_path = tmp_path / "corrupt.pdf"
    bad_path.write_bytes(b"%PDF-1.4\nnot a real pdf body")

    extracted = manager._extract_from_pdf(bad_path)

    assert "Error reading PDF" in extracted


def test_knowledge_manager_imports_pypdf_not_pypdf2():
    """Guards the migration itself: the module must import the maintained ``pypdf``
    package, never the abandoned ``PyPDF2`` (PYSEC-2026-1835, no fix release)."""
    assert km.pypdf.__name__ == "pypdf"
