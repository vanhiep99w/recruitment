"""
LLM proxy client — supports both Azure OpenAI and generic OpenAI-compatible endpoints.

Usage:
    client = LLMClient(base_url="https://api.openai.com/v1", api_key="sk-...")
    response = await client.chat_complete(messages=[...], model="gpt-4o-mini")
    embedding = await client.embed(text="...", model="text-embedding-ada-002")
"""
from __future__ import annotations

import json
from typing import Any

from openai import AsyncAzureOpenAI, AsyncOpenAI

from app.config import settings


class LLMClient:
    """
    OpenAI-compatible LLM client.

    Supports:
    - Standard OpenAI / OpenAI-compatible proxies (base_url + api_key)
    - Azure OpenAI (api_version triggers Azure client)
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        api_version: str | None = None,
        azure_deployment: str | None = None,
    ) -> None:
        self._base_url = base_url or settings.LLM_BASE_URL
        self._api_key = api_key or settings.LLM_API_KEY
        self._api_version = api_version or settings.LLM_API_VERSION
        self._azure_deployment = azure_deployment or settings.LLM_DEPLOYMENT_NAME
        self._client: AsyncOpenAI | AsyncAzureOpenAI | None = None

    def _get_openai_client(self) -> AsyncOpenAI | AsyncAzureOpenAI:
        """Lazily create and return the underlying OpenAI client."""
        if self._client is None:
            if self._api_version:
                # Azure OpenAI path
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=self._base_url,
                    api_key=self._api_key,
                    api_version=self._api_version,
                )
            else:
                # Standard OpenAI / compatible proxy
                self._client = AsyncOpenAI(
                    base_url=self._base_url,
                    api_key=self._api_key,
                )
        return self._client

    async def chat_complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Call the chat completions endpoint and return the assistant message content.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts.
            model: Model identifier. Defaults to settings.LLM_CHAT_MODEL.
            temperature: Sampling temperature (0.0–2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters forwarded to the API.

        Returns:
            The assistant's response text.
        """
        client = self._get_openai_client()
        effective_model = model or settings.LLM_CHAT_MODEL

        params: dict[str, Any] = {
            "model": effective_model,
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        response = await client.chat.completions.create(**params)
        return response.choices[0].message.content or ""

    async def embed(
        self,
        text: str | list[str],
        model: str | None = None,
        **kwargs: Any,
    ) -> list[float] | list[list[float]]:
        """
        Generate embeddings for the given text(s).

        Args:
            text: A single string or a list of strings to embed.
            model: Embedding model identifier. Defaults to settings.LLM_EMBED_MODEL.
            **kwargs: Additional parameters forwarded to the API.

        Returns:
            A single embedding vector (list[float]) for a single input,
            or a list of embedding vectors for a list input.
        """
        client = self._get_openai_client()
        effective_model = model or settings.LLM_EMBED_MODEL
        input_texts = text if isinstance(text, list) else [text]

        response = await client.embeddings.create(
            model=effective_model,
            input=input_texts,
            **kwargs,
        )

        embeddings = [item.embedding for item in response.data]
        # Return a single vector when a single string was passed
        return embeddings[0] if isinstance(text, str) else embeddings

    async def parse_cv(self, text: str) -> dict[str, Any]:
        """Parse raw CV text into structured candidate profile data."""

        response = await self.chat_complete(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract a candidate profile from CV text. "
                        "Return compact JSON with keys: name, email, phone, location, "
                        "skills, work_experience, education, languages, certifications."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        return json.loads(response)

    async def parse_jd(self, text: str) -> dict[str, Any]:
        """Parse raw job description text into structured JD profile data."""

        response = await self.chat_complete(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract a structured job profile from the provided job description. "
                        "Return JSON with keys: title, required_skills, nice_to_have_skills, "
                        "seniority, experience_years_min, experience_years_max, responsibilities."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        return json.loads(response)

    async def generate_match_rationale(
        self,
        *,
        candidate_summary: dict[str, Any],
        job_summary: dict[str, Any],
        scores: dict[str, int],
    ) -> str:
        """Generate a short, recruiter-facing rationale for a candidate/job match."""

        response = await self.chat_complete(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You explain candidate-job match scores to recruiters. "
                        "Return a single plain-text rationale under 200 characters."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "candidate": candidate_summary,
                            "job": job_summary,
                            "scores": scores,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=120,
        )
        return response.strip()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.close()
            self._client = None


# Module-level default client (lazy-initialized)
_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Return the module-level default LLM client (FastAPI dependency)."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
