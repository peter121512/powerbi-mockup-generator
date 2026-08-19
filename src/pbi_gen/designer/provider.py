"""LLM provider abstraction and concrete Bedrock implementation.

The provider boundary keeps vendor-specific SDK details out of domain logic.
Tests can substitute a mock provider without network access.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for an LLM provider."""

    provider: str = "bedrock"
    model_id: str = "anthropic.claude-sonnet-4-20250514-v1:0"
    region: str = "eu-west-2"
    max_tokens: int = 16384
    temperature: float = 0.4
    timeout_seconds: int = 120


@dataclass(frozen=True)
class ProviderResponse:
    """Raw response from a provider call."""

    content: str  # The text/JSON content returned
    model_id: str = ""
    stop_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class ProviderError(Exception):
    """Raised when a provider call fails."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class LLMProvider(ABC):
    """Abstract interface for LLM providers.

    The application only depends on this interface. Concrete implementations
    wrap vendor SDKs.
    """

    @abstractmethod
    def generate_structured(
        self,
        system_prompt: str,
        user_message: str,
        json_schema: dict | None = None,
    ) -> ProviderResponse:
        """Generate a structured (JSON) response from the model.

        Args:
            system_prompt: System-level instructions.
            user_message: The user's request.
            json_schema: Optional JSON schema to constrain output format.

        Returns:
            ProviderResponse with JSON content.

        Raises:
            ProviderError: If the model call fails.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier used for diagnostics."""
        ...


class BedrockProvider(LLMProvider):
    """Amazon Bedrock provider using the Converse API.

    Requires AWS credentials configured via environment, AWS CLI profile,
    or IAM role. No credentials are stored in code.
    """

    def __init__(self, config: ProviderConfig | None = None):
        self._config = config or ProviderConfig()
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Bedrock Runtime client."""
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self._config.region,
            )
        return self._client

    @property
    def provider_name(self) -> str:
        return "bedrock"

    @property
    def model_name(self) -> str:
        return self._config.model_id

    def generate_structured(
        self,
        system_prompt: str,
        user_message: str,
        json_schema: dict | None = None,
    ) -> ProviderResponse:
        """Call Bedrock Converse API for structured JSON output."""
        client = self._get_client()

        messages = [
            {
                "role": "user",
                "content": [{"text": user_message}],
            }
        ]

        system = [{"text": system_prompt}]

        inference_config = {
            "maxTokens": self._config.max_tokens,
            "temperature": self._config.temperature,
        }

        try:
            kwargs = {
                "modelId": self._config.model_id,
                "messages": messages,
                "system": system,
                "inferenceConfig": inference_config,
            }

            response = client.converse(**kwargs)

            # Extract response content
            output = response.get("output", {})
            message = output.get("message", {})
            content_blocks = message.get("content", [])

            text_content = ""
            for block in content_blocks:
                if "text" in block:
                    text_content += block["text"]

            # Extract usage info
            usage = response.get("usage", {})
            stop_reason = response.get("stopReason", "")

            return ProviderResponse(
                content=text_content,
                model_id=self._config.model_id,
                stop_reason=stop_reason,
                input_tokens=usage.get("inputTokens", 0),
                output_tokens=usage.get("outputTokens", 0),
            )

        except Exception as e:
            error_name = type(e).__name__
            # Classify retryable errors
            retryable = any(
                keyword in error_name.lower()
                for keyword in ["throttl", "timeout", "service"]
            )
            raise ProviderError(
                f"Bedrock call failed: {error_name}: {e}",
                retryable=retryable,
            ) from e
