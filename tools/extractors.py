"""
Text extraction from various book formats.
"""

import subprocess
import tempfile
from pathlib import Path


def extract_text(file_path: str) -> str:
    """
    Extract text from EPUB, MOBI, or PDF.
    Returns full text content.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return extract_pdf(path)
    elif suffix in (".epub", ".mobi", ".azw", ".azw3"):
        return extract_ebook(path)
    elif suffix == ".txt":
        return path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported format: {suffix}")


def extract_pdf(path: Path) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber required: pip install pdfplumber")

    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return "\n\n".join(text_parts)


def extract_ebook(path: Path) -> str:
    """
    Extract text from EPUB/MOBI using Calibre's ebook-convert.
    Falls back to ebooklib for EPUB if Calibre not available.
    """
    # Try Calibre first (handles MOBI well)
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name

        result = subprocess.run(
            ["ebook-convert", str(path), tmp_path],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            text = Path(tmp_path).read_text(encoding="utf-8")
            Path(tmp_path).unlink()
            return text
    except FileNotFoundError:
        pass  # Calibre not installed

    # Fallback: use ebooklib for EPUB
    if path.suffix.lower() == ".epub":
        return extract_epub_native(path)

    raise RuntimeError(
        f"Cannot extract {path.suffix}. Install Calibre: brew install calibre"
    )


def extract_epub_native(path: Path) -> str:
    """Extract text from EPUB using ebooklib."""
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError(
            "ebooklib and beautifulsoup4 required: "
            "pip install ebooklib beautifulsoup4"
        )

    book = epub.read_epub(str(path))
    text_parts = []

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n")
            if text.strip():
                text_parts.append(text)

    return "\n\n".join(text_parts)
