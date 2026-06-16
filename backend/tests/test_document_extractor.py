import base64
from unittest.mock import MagicMock, patch

from media_agents.agents.document_extractor import extract_text


def _make_data_url(content: bytes, mime: str) -> str:
    encoded = base64.b64encode(content).decode()
    return f"data:{mime};base64,{encoded}"


def test_extract_plain_text():
    text = "Hello, world! This is a test document."
    data_url = _make_data_url(text.encode("utf-8"), "text/plain")
    result = extract_text(data_url, "text/plain", "test.txt")
    assert result == text


def test_extract_markdown():
    md = "# Heading\n\nSome **bold** text."
    data_url = _make_data_url(md.encode("utf-8"), "text/markdown")
    result = extract_text(data_url, "text/markdown", "readme.md")
    assert result == md


def test_extract_truncates_long_text():
    long_text = "a" * 60_000
    data_url = _make_data_url(long_text.encode("utf-8"), "text/plain")
    result = extract_text(data_url, "text/plain", "big.txt")
    assert len(result) <= 50_000
    assert result.endswith("…[truncated]")


def test_extract_unsupported_mime_returns_fallback():
    data_url = _make_data_url(b"binary junk", "application/octet-stream")
    result = extract_text(data_url, "application/octet-stream", "mystery.bin")
    assert "[Could not extract text from mystery.bin]" in result


def test_extract_invalid_base64_returns_fallback():
    result = extract_text("data:text/plain;base64,!!!invalid!!!", "text/plain", "bad.txt")
    assert "[Could not extract text from bad.txt]" in result


def test_extract_pdf():
    mock_reader = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page 1 Content"
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Page 2 Content"
    mock_reader.pages = [mock_page1, mock_page2]
    
    with patch("pypdf.PdfReader", return_value=mock_reader) as mock_pdf_reader:
        data_url = _make_data_url(b"fake pdf content", "application/pdf")
        result = extract_text(data_url, "application/pdf", "test.pdf")
        
        mock_pdf_reader.assert_called_once()
        assert result == "Page 1 Content\n\nPage 2 Content"


def test_extract_docx_paragraphs_and_tables():
    mock_doc = MagicMock()
    
    # Set up paragraphs
    mock_p1 = MagicMock()
    mock_p1.text = "Paragraph 1"
    mock_p2 = MagicMock()
    mock_p2.text = "   "  # empty/whitespace paragraph
    mock_p3 = MagicMock()
    mock_p3.text = "Paragraph 3"
    mock_doc.paragraphs = [mock_p1, mock_p2, mock_p3]
    
    # Set up tables
    mock_table = MagicMock()
    mock_row1 = MagicMock()
    mock_cell1 = MagicMock()
    mock_cp1 = MagicMock()
    mock_cp1.text = "Cell Paragraph 1"
    mock_cell1.paragraphs = [mock_cp1]
    
    mock_cell2 = MagicMock()
    mock_cp2 = MagicMock()
    mock_cp2.text = ""  # empty paragraph in cell
    mock_cell2.paragraphs = [mock_cp2]
    
    mock_row1.cells = [mock_cell1, mock_cell2]
    mock_table.rows = [mock_row1]
    mock_doc.tables = [mock_table]
    
    with patch("docx.Document", return_value=mock_doc) as mock_docx_doc:
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        data_url = _make_data_url(b"fake docx content", mime)
        result = extract_text(data_url, mime, "test.docx")
        
        mock_docx_doc.assert_called_once()
        assert result == "Paragraph 1\n\nParagraph 3\n\nCell Paragraph 1"


def test_extract_malformed_data_url():
    result = extract_text("data:text/plain;base64;no-comma-here", "text/plain", "malformed.txt")
    assert result == "[Could not extract text from malformed.txt]"


def test_extract_mime_type_with_parameters():
    text = "MIME parameters test"
    data_url = _make_data_url(text.encode("utf-8"), "text/plain")
    
    result = extract_text(data_url, "text/plain; charset=utf-8", "param.txt")
    assert result == text
    
    result2 = extract_text(data_url, " TEXT/plain ; charset=UTF-8 ", "param.txt")
    assert result2 == text


def test_extract_unicode_replace_behavior():
    bad_utf8 = b"Hello \xff\xfe World"
    data_url = _make_data_url(bad_utf8, "text/plain")
    result = extract_text(data_url, "text/plain", "unicode.txt")
    assert "\ufffd" in result
    assert "Hello " in result
    assert " World" in result


def test_extract_truncation_negative_slice_edge_case():
    with patch("media_agents.agents.document_extractor._MAX_TEXT_LENGTH", 5):
        text = "Hello world"
        data_url = _make_data_url(text.encode("utf-8"), "text/plain")
        result = extract_text(data_url, "text/plain", "trunc.txt")
        assert result == "…[truncated]"
