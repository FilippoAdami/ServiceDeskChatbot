from __future__ import annotations

import hashlib
import math
import re
from typing import List

from backend.app.rag.embeddings.base import BaseEmbeddingEncoder


class DeterministicFakeEncoder(BaseEmbeddingEncoder):
    """Deterministic, offline fake embedding generator for tests and non-ML environments.

    Uses a feature-hashing scheme with L2 normalization to produce 1024-dimensional vectors.
    Preserves lexical overlap so queries retrieve relevant documents in offline tests without
    requiring model weights, internet access, or GPU.
    """

    def __init__(self, dimension: int = 1024, model_name: str = "fake-bge-m3-deterministic") -> None:
        self._dim = dimension
        self._model_name = model_name

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    def _hash_vector(self, text: str) -> List[float]:
        vector = [0.0] * self._dim
        clean = text.lower()
        tokens = re.findall(r"\w+", clean)

        if not tokens:
            tokens = ["empty"]

        for token in tokens:
            # Hash token to a dimension index and sign
            h = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "big") % self._dim
            sign = 1.0 if (h[4] % 2 == 0) else -1.0
            vector[idx] += sign

        # Add character bi-grams for partial match support
        for i in range(len(clean) - 1):
            bigram = clean[i : i + 2]
            h = hashlib.md5(bigram.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "big") % self._dim
            vector[idx] += 0.25

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0.0:
            vector = [v / norm for v in vector]
        else:
            vector[0] = 1.0

        return vector

    def encode_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_vector(t) for t in texts]

    def encode_queries(self, queries: List[str]) -> List[List[float]]:
        return [self._hash_vector(q) for q in queries]
