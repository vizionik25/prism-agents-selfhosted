import base64
from fastapi import HTTPException
import pytest

from media_agents.services.chat import ChatAttachment, validate_attachments


def _make_attachment(
    filename: str = "test.png",
    mime_type: str = "image/png",
    size_bytes: int = 100,
) -> ChatAttachment:
    data = base64.b64encode(b"\x00" * size_bytes).decode()
    return ChatAttachment(
        filename=filename,
        mime_type=mime_type,
        data_url=f"data:{mime_type};base64,{data}",
    )


def test_validate_empty_list():
    validate_attachments([])  # should not raise


def test_validate_valid_attachments():
    attachments = [
        _make_attachment("photo.jpg", "image/jpeg"),
        _make_attachment("doc.pdf", "application/pdf"),
    ]
    validate_attachments(attachments)  # should not raise


def test_validate_rejects_too_many():
    attachments = [_make_attachment(f"file{i}.png") for i in range(6)]
    with pytest.raises(HTTPException) as excinfo:
        validate_attachments(attachments)
    assert excinfo.value.status_code == 400
    assert "Maximum 5 attachments" in excinfo.value.detail


def test_validate_rejects_unsupported_mime():
    attachments = [_make_attachment("evil.exe", "application/x-msdownload")]
    with pytest.raises(HTTPException) as excinfo:
        validate_attachments(attachments)
    assert excinfo.value.status_code == 400
    assert "Unsupported file type" in excinfo.value.detail


def test_validate_rejects_oversized_image(monkeypatch):
    from media_agents.services.chat import _SIZE_LIMITS
    monkeypatch.setitem(_SIZE_LIMITS, "image", 100)

    # 150 bytes image — over the 100 bytes limit
    attachments = [_make_attachment("big.jpg", "image/jpeg", size_bytes=150)]
    with pytest.raises(HTTPException) as excinfo:
        validate_attachments(attachments)
    assert excinfo.value.status_code == 400
    assert "exceeds" in excinfo.value.detail
    assert "exceeds 0.0MB limit" in excinfo.value.detail


def test_validate_accepts_mime_with_parameters():
    # test that we handle headers like "image/png; charset=utf-8" gracefully
    att = _make_attachment("photo.png", "image/png; charset=utf-8")
    validate_attachments([att])  # should not raise


def test_validate_rejects_invalid_base64():
    # Case 1: Missing comma separator
    att_no_comma = ChatAttachment(
        filename="test.png",
        mime_type="image/png",
        data_url="data:image/png;base64XYZ"
    )
    with pytest.raises(HTTPException) as excinfo:
        validate_attachments([att_no_comma])
    assert excinfo.value.status_code == 400
    assert "Invalid base64 data for test.png" in excinfo.value.detail

    # Case 2: Invalid base64 data
    att_invalid_b64 = ChatAttachment(
        filename="test.png",
        mime_type="image/png",
        data_url="data:image/png;base64,invalid_b64!!!"
    )
    with pytest.raises(HTTPException) as excinfo:
        validate_attachments([att_invalid_b64])
    assert excinfo.value.status_code == 400
    assert "Invalid base64 data for test.png" in excinfo.value.detail


def test_validate_early_size_check_with_padding(monkeypatch):
    # Set limit to 2 bytes
    from media_agents.services.chat import _SIZE_LIMITS
    monkeypatch.setitem(_SIZE_LIMITS, "image", 2)

    # 3 bytes image - exceeds 2 bytes limit
    att_3 = _make_attachment("photo.png", "image/png", size_bytes=3)
    with pytest.raises(HTTPException) as excinfo:
        validate_attachments([att_3])
    assert excinfo.value.status_code == 400
    assert "exceeds" in excinfo.value.detail

    # 2 bytes image - exactly equals the limit of 2, should pass due to padding deduction
    att_2 = _make_attachment("photo.png", "image/png", size_bytes=2)
    validate_attachments([att_2])  # should not raise
