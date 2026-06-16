"""Tests for multimodal message construction in the fal model adapter."""

import base64

import pytest
from pydantic_ai.messages import ModelRequest, UserPromptPart

from media_agents.agents.fal_model import _messages_to_openai


@pytest.mark.asyncio
async def test_plain_text_message_unchanged():
    """Without attachments, user messages remain simple strings."""
    messages = [ModelRequest(parts=[UserPromptPart(content="hello")])]
    result = await _messages_to_openai(messages)
    assert result == [{"role": "user", "content": "hello"}]


@pytest.mark.asyncio
async def test_image_attachment_creates_content_array():
    """An image attachment should produce a content array with image_url + text parts."""
    data_url = f"data:image/png;base64,{base64.b64encode(b'fakepng').decode()}"
    attachments = [{"filename": "photo.png", "mime_type": "image/png", "data_url": data_url}]
    messages = [ModelRequest(parts=[UserPromptPart(content="describe this")])]
    result = await _messages_to_openai(messages, attachments=attachments)

    assert len(result) == 1
    content = result[0]["content"]
    assert isinstance(content, list)
    assert content[0] == {"type": "image_url", "image_url": {"url": data_url}}
    assert content[-1] == {"type": "text", "text": "describe this"}


@pytest.mark.asyncio
async def test_document_attachment_injects_text():
    """A text document should be extracted and prepended to the user message text."""
    text_content = "Document body here."
    encoded = base64.b64encode(text_content.encode()).decode()
    data_url = f"data:text/plain;base64,{encoded}"
    attachments = [{"filename": "notes.txt", "mime_type": "text/plain", "data_url": data_url}]
    messages = [ModelRequest(parts=[UserPromptPart(content="summarize")])]
    result = await _messages_to_openai(messages, attachments=attachments)

    content = result[0]["content"]
    # Should be a plain string (no image parts, just enriched text)
    assert isinstance(content, str)
    assert "[Document: notes.txt]" in content
    assert text_content in content
    assert "summarize" in content


@pytest.mark.asyncio
async def test_mixed_attachments():
    """Image + document = content array with image_url + enriched text."""
    img_url = f"data:image/jpeg;base64,{base64.b64encode(b'fakejpg').decode()}"
    doc_text = "Important context."
    doc_url = f"data:text/plain;base64,{base64.b64encode(doc_text.encode()).decode()}"
    attachments = [
        {"filename": "ref.jpg", "mime_type": "image/jpeg", "data_url": img_url},
        {"filename": "brief.txt", "mime_type": "text/plain", "data_url": doc_url},
    ]
    messages = [ModelRequest(parts=[UserPromptPart(content="use these")])]
    result = await _messages_to_openai(messages, attachments=attachments)

    content = result[0]["content"]
    assert isinstance(content, list)
    # First element is the image
    assert content[0]["type"] == "image_url"
    # Last element is text with the document content prepended
    text_part = content[-1]
    assert text_part["type"] == "text"
    assert "[Document: brief.txt]" in text_part["text"]
    assert "use these" in text_part["text"]


@pytest.mark.asyncio
async def test_no_attachments_on_non_last_message():
    """Attachments should only affect the last user message."""
    img_url = f"data:image/png;base64,{base64.b64encode(b'fake').decode()}"
    attachments = [{"filename": "img.png", "mime_type": "image/png", "data_url": img_url}]
    messages = [
        ModelRequest(parts=[UserPromptPart(content="first message")]),
        ModelRequest(parts=[UserPromptPart(content="second message")]),
    ]
    result = await _messages_to_openai(messages, attachments=attachments)

    # First message: plain string
    assert result[0]["content"] == "first message"
    # Second (last) message: content array with attachment
    assert isinstance(result[1]["content"], list)


@pytest.mark.asyncio
async def test_video_attachment_creates_text_marker():
    """A video attachment should produce a text marker in the user message instead of image_url."""
    data_url = "data:video/mp4;base64,ZmFrZXZpZGVv"
    attachments = [{"filename": "clip.mp4", "mime_type": "video/mp4", "data_url": data_url}]
    messages = [ModelRequest(parts=[UserPromptPart(content="analyze")])]
    result = await _messages_to_openai(messages, attachments=attachments)

    content = result[0]["content"]
    assert isinstance(content, str)
    assert "[Attached Video: clip.mp4]" in content
    assert "[End video]" in content
    assert "analyze" in content


def test_nested_token_reset_behavior():
    """Verify that setting and resetting attachments behaves correctly with nested runs using contextvars.Token."""
    from media_agents.agents.fal_model import (
        get_current_attachments,
        reset_current_attachments,
        set_current_attachments,
    )

    assert get_current_attachments() is None

    # Outer run sets attachments
    outer_att = [{"filename": "outer.png", "mime_type": "image/png", "data_url": "outer_url"}]
    outer_token = set_current_attachments(outer_att)
    assert get_current_attachments() == outer_att

    # Inner run sets attachments
    inner_att = [{"filename": "inner.png", "mime_type": "image/png", "data_url": "inner_url"}]
    inner_token = set_current_attachments(inner_att)
    assert get_current_attachments() == inner_att

    # Reset inner run
    reset_current_attachments(inner_token)
    assert get_current_attachments() == outer_att

    # Reset outer run
    reset_current_attachments(outer_token)
    assert get_current_attachments() is None
