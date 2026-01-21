# src/services/embedding_service.py
"""Embedding generation service using OpenAI."""

import os
from typing import Optional

from openai import AsyncOpenAI
import structlog

log = structlog.get_logger()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            log.warning("openai_api_key_not_set", message="Embeddings will not work")
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            List of floats (1536 dimensions)
        """
        if not self.client:
            log.warning("embedding_skipped", reason="no_api_key")
            return [0.0] * EMBEDDING_DIMENSIONS

        try:
            response = await self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text,
            )
            embedding = response.data[0].embedding
            log.info("embedding_generated", text_length=len(text))
            return embedding
        except Exception as e:
            log.error("embedding_error", error=str(e))
            return [0.0] * EMBEDDING_DIMENSIONS

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        if not self.client:
            return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]

        try:
            response = await self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]
            log.info("embeddings_generated", count=len(texts))
            return embeddings
        except Exception as e:
            log.error("embeddings_error", error=str(e))
            return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]
