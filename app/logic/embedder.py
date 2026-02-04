"""Embedding generation and similarity functions."""

import logging
import openai
import numpy as np

from app.config import OPENAI_API_KEY, MODEL_EMBEDDING
from app.utils.retry import retry

logger = logging.getLogger(__name__)

openai.api_key = OPENAI_API_KEY


@retry(max_attempts=3, delay=1.0, exceptions=(Exception,))
def get_embedding(text: str) -> list:
    """
    Generate an embedding vector for the given text.

    Args:
        text: The text to embed

    Returns:
        List of floats representing the embedding vector
    """
    if not text.strip():
        return [0.0] * 1536

    # Truncate if too long (~8000 tokens ~ ~30K chars)
    if len(text) > 30000:
        text = text[:30000]

    response = openai.embeddings.create(
        model=MODEL_EMBEDDING,
        input=text.strip()
    )
    return response.data[0].embedding


def cosine_similarity(vec1: list, vec2: list) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Similarity score between 0 and 1
    """
    a = np.array(vec1)
    b = np.array(vec2)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
