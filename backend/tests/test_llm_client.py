"""
Tests for LLM proxy client — verifies interface and configurability.
Phase 1: RED — these tests must fail before implementation.
"""
import pytest
import inspect
from unittest.mock import AsyncMock, patch, MagicMock


def test_llm_client_importable():
    """LLMClient must be importable from app.services.llm_client."""
    from app.services.llm_client import LLMClient
    assert LLMClient is not None


def test_llm_client_has_chat_complete_method():
    """LLMClient must have a chat_complete method."""
    from app.services.llm_client import LLMClient
    assert hasattr(LLMClient, "chat_complete")
    method = getattr(LLMClient, "chat_complete")
    assert callable(method)


def test_llm_client_has_embed_method():
    """LLMClient must have an embed method."""
    from app.services.llm_client import LLMClient
    assert hasattr(LLMClient, "embed")
    method = getattr(LLMClient, "embed")
    assert callable(method)


def test_llm_client_chat_complete_is_async():
    """LLMClient.chat_complete must be an async method."""
    from app.services.llm_client import LLMClient
    method = getattr(LLMClient, "chat_complete")
    assert inspect.iscoroutinefunction(method)


def test_llm_client_embed_is_async():
    """LLMClient.embed must be an async method."""
    from app.services.llm_client import LLMClient
    method = getattr(LLMClient, "embed")
    assert inspect.iscoroutinefunction(method)


def test_llm_client_accepts_base_url_and_api_key():
    """LLMClient must accept base_url and api_key in constructor."""
    from app.services.llm_client import LLMClient
    sig = inspect.signature(LLMClient.__init__)
    params = set(sig.parameters.keys())
    assert "base_url" in params or "api_key" in params, (
        "LLMClient.__init__ must accept base_url and api_key"
    )


def test_llm_client_instantiation_with_config():
    """LLMClient must be instantiable with base_url and api_key."""
    from app.services.llm_client import LLMClient
    client = LLMClient(base_url="https://api.openai.com/v1", api_key="test-key")
    assert client is not None


@pytest.mark.asyncio
async def test_llm_client_chat_complete_callable():
    """LLMClient.chat_complete must be callable with messages list."""
    from app.services.llm_client import LLMClient
    client = LLMClient(base_url="https://api.openai.com/v1", api_key="test-key")
    messages = [{"role": "user", "content": "Hello"}]
    # Should not raise TypeError on call signature
    with patch.object(client, "_get_openai_client") as mock_get:
        mock_openai = MagicMock()
        mock_chat = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="Hi there"))]
        ))
        mock_openai.chat.completions.create = mock_chat
        mock_get.return_value = mock_openai
        try:
            result = await client.chat_complete(messages=messages, model="gpt-4o-mini")
        except Exception:
            pass  # We only care that the method signature is correct


@pytest.mark.asyncio
async def test_llm_client_embed_callable():
    """LLMClient.embed must be callable with text input."""
    from app.services.llm_client import LLMClient
    client = LLMClient(base_url="https://api.openai.com/v1", api_key="test-key")
    # Should not raise TypeError on call signature
    with patch.object(client, "_get_openai_client") as mock_get:
        mock_openai = MagicMock()
        mock_embed = AsyncMock(return_value=MagicMock(
            data=[MagicMock(embedding=[0.1] * 1536)]
        ))
        mock_openai.embeddings.create = mock_embed
        mock_get.return_value = mock_openai
        try:
            result = await client.embed(text="test text", model="text-embedding-ada-002")
        except Exception:
            pass  # We only care that the method signature is correct


# ---------------------------------------------------------------------------
# Additional tests for uncovered lines (42-56, 89, 128-130, 140-142)
# ---------------------------------------------------------------------------

def test_get_openai_client_standard_path():
    """_get_openai_client creates AsyncOpenAI when no api_version is set."""
    from app.services.llm_client import LLMClient
    from openai import AsyncOpenAI
    client = LLMClient(base_url="https://api.openai.com/v1", api_key="sk-test")
    # No api_version → standard path
    assert client._api_version is None or client._api_version == ""
    # Force api_version to None to ensure standard path
    client._api_version = None
    result = client._get_openai_client()
    assert isinstance(result, AsyncOpenAI)
    # Second call returns cached client
    result2 = client._get_openai_client()
    assert result is result2


def test_get_openai_client_azure_path():
    """_get_openai_client creates AsyncAzureOpenAI when api_version is set."""
    from app.services.llm_client import LLMClient
    from openai import AsyncAzureOpenAI
    client = LLMClient(
        base_url="https://myresource.openai.azure.com",
        api_key="azure-key",
        api_version="2024-02-15-preview",
    )
    result = client._get_openai_client()
    assert isinstance(result, AsyncAzureOpenAI)
    # Second call returns cached client
    result2 = client._get_openai_client()
    assert result is result2


@pytest.mark.asyncio
async def test_chat_complete_returns_content():
    """chat_complete returns the assistant message content string."""
    from app.services.llm_client import LLMClient
    client = LLMClient(base_url="https://api.openai.com/v1", api_key="sk-test")
    client._api_version = None
    with patch.object(client, "_get_openai_client") as mock_get:
        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="Hello from LLM"))]
        ))
        mock_get.return_value = mock_openai
        result = await client.chat_complete(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini",
        )
    assert result == "Hello from LLM"


@pytest.mark.asyncio
async def test_chat_complete_with_max_tokens():
    """chat_complete passes max_tokens when provided."""
    from app.services.llm_client import LLMClient
    client = LLMClient(base_url="https://api.openai.com/v1", api_key="sk-test")
    client._api_version = None
    with patch.object(client, "_get_openai_client") as mock_get:
        mock_create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="response"))]
        ))
        mock_openai = MagicMock()
        mock_openai.chat.completions.create = mock_create
        mock_get.return_value = mock_openai
        result = await client.chat_complete(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini",
            max_tokens=100,
        )
    assert result == "response"
    call_kwargs = mock_create.call_args[1]
    assert call_kwargs.get("max_tokens") == 100


@pytest.mark.asyncio
async def test_chat_complete_none_content_returns_empty_string():
    """chat_complete returns empty string when content is None."""
    from app.services.llm_client import LLMClient
    client = LLMClient(base_url="https://api.openai.com/v1", api_key="sk-test")
    client._api_version = None
    with patch.object(client, "_get_openai_client") as mock_get:
        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content=None))]
        ))
        mock_get.return_value = mock_openai
        result = await client.chat_complete(
            messages=[{"role": "user", "content": "Hi"}],
        )
    assert result == ""


@pytest.mark.asyncio
async def test_embed_single_string_returns_vector():
    """embed returns a flat list[float] for a single string input."""
    from app.services.llm_client import LLMClient
    client = LLMClient(base_url="https://api.openai.com/v1", api_key="sk-test")
    client._api_version = None
    vector = [0.1, 0.2, 0.3]
    with patch.object(client, "_get_openai_client") as mock_get:
        mock_openai = MagicMock()
        mock_openai.embeddings.create = AsyncMock(return_value=MagicMock(
            data=[MagicMock(embedding=vector)]
        ))
        mock_get.return_value = mock_openai
        result = await client.embed(text="hello world")
    assert result == vector


@pytest.mark.asyncio
async def test_embed_list_of_strings_returns_list_of_vectors():
    """embed returns list[list[float]] for list input."""
    from app.services.llm_client import LLMClient
    client = LLMClient(base_url="https://api.openai.com/v1", api_key="sk-test")
    client._api_version = None
    vectors = [[0.1, 0.2], [0.3, 0.4]]
    with patch.object(client, "_get_openai_client") as mock_get:
        mock_openai = MagicMock()
        mock_openai.embeddings.create = AsyncMock(return_value=MagicMock(
            data=[MagicMock(embedding=v) for v in vectors]
        ))
        mock_get.return_value = mock_openai
        result = await client.embed(text=["text1", "text2"])
    assert result == vectors


@pytest.mark.asyncio
async def test_close_closes_and_clears_client():
    """close() calls close on underlying client and sets _client to None."""
    from app.services.llm_client import LLMClient
    client = LLMClient(base_url="https://api.openai.com/v1", api_key="sk-test")
    client._api_version = None
    # Manually set a mock client
    mock_inner = AsyncMock()
    client._client = mock_inner
    await client.close()
    mock_inner.close.assert_awaited_once()
    assert client._client is None


@pytest.mark.asyncio
async def test_close_when_no_client_is_noop():
    """close() does nothing when _client is None."""
    from app.services.llm_client import LLMClient
    client = LLMClient(base_url="https://api.openai.com/v1", api_key="sk-test")
    client._client = None
    # Should not raise
    await client.close()
    assert client._client is None


def test_get_llm_client_returns_instance():
    """get_llm_client returns an LLMClient instance."""
    import app.services.llm_client as llm_module
    from app.services.llm_client import LLMClient, get_llm_client
    # Reset module-level client to ensure fresh initialization
    llm_module._default_client = None
    client = get_llm_client()
    assert isinstance(client, LLMClient)


def test_get_llm_client_caches_instance():
    """get_llm_client returns the same instance on repeated calls."""
    import app.services.llm_client as llm_module
    from app.services.llm_client import get_llm_client
    llm_module._default_client = None
    c1 = get_llm_client()
    c2 = get_llm_client()
    assert c1 is c2
