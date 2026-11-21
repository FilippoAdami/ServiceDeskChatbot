from __future__ import annotations

import logging
from typing import Any, List, Optional

from backend.app.rag.embeddings.base import BaseEmbeddingEncoder

logger = logging.getLogger(__name__)


class BGEM3Encoder(BaseEmbeddingEncoder):
    """BGE-M3 Dense Embedding Encoder using FlagEmbedding.

    Lazy loads the underlying FlagModel only upon first encoding call or explicit load().
    Outputs 1024-dimensional normalized dense vectors.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cpu",
        use_fp16: bool = False,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._use_fp16 = use_fp16
        self._model: Optional[Any] = None
        self._dim: int = 1024

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    def _ensure_loaded(self) -> Any:
        if self._model is None:
            logger.info(
                "Lazy-loading BGE-M3 model '%s' on device '%s' (fp16=%s)...",
                self._model_name,
                self._device,
                self._use_fp16,
            )
            try:
                from FlagEmbedding import BGEM3FlagModel  # type: ignore[import-untyped]

                self._model = BGEM3FlagModel(
                    self._model_name,
                    use_fp16=self._use_fp16,
                    device=self._device,
                )
            except Exception as e:
                logger.error("Failed to load BGEM3FlagModel: %s", e)
                raise RuntimeError(
                    f"Could not load BGE-M3 model '{self._model_name}': {e}. "
                    "Ensure FlagEmbedding and PyTorch are installed and model weights are accessible."
                ) from e
        return self._model

    def encode_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self._ensure_loaded()
        # BGEM3FlagModel.encode returns a dict with 'dense_vecs', 'lexical_weights', etc.
        # or numpy array depending on parameters.
        result = model.encode(
            texts,
            batch_size=12,
            max_length=8192,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        if isinstance(result, dict) and "dense_vecs" in result:
            dense = result["dense_vecs"]
        else:
            dense = result
        return [vec.tolist() if hasattr(vec, "tolist") else list(vec) for vec in dense]

    def encode_queries(self, queries: List[str]) -> List[List[float]]:
        if not queries:
            return []
        model = self._ensure_loaded()
        result = model.encode(
            queries,
            batch_size=12,
            max_length=1024,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        if isinstance(result, dict) and "dense_vecs" in result:
            dense = result["dense_vecs"]
        else:
            dense = result
        return [vec.tolist() if hasattr(vec, "tolist") else list(vec) for vec in dense]
