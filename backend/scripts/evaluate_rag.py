#!/usr/bin/env python3
"""Evaluation benchmark script for Service Desk Knowledge Base semantic retrieval.

Measures Recall@5, MRR@5, and latency (p50, p95, mean) on Italian service desk queries.
Supports both BGE-M3 (FlagEmbedding) and DeterministicFakeEncoder (offline tests).
"""

import argparse
import json
import logging
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.config import get_settings
from backend.app.rag.embeddings.base import BaseEmbeddingEncoder
from backend.app.rag.embeddings.bge_m3 import BGEM3Encoder
from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.service import KnowledgeRetrievalService
from backend.app.rag.vector_store.chroma import ChromaVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_rag")


def run_evaluation(
    dataset_path: Path,
    service: KnowledgeRetrievalService,
    top_k: int = 5,
    use_multi_query: bool = True,
) -> Dict[str, Any]:
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset: List[Dict[str, Any]] = json.load(f)

    in_scope_queries = [q for q in dataset if q.get("expected_doc_ids")]
    out_of_scope_queries = [q for q in dataset if not q.get("expected_doc_ids")]

    logger.info(
        "Running evaluation on %d total queries (%d in-scope, %d out-of-scope)...",
        len(dataset),
        len(in_scope_queries),
        len(out_of_scope_queries),
    )

    latencies_ms: List[float] = []
    recall_hits = 0
    reciprocal_ranks: List[float] = []
    query_reports: List[Dict[str, Any]] = []

    for item in in_scope_queries:
        qid = item["id"]
        query = item["query"]
        sub_queries = item.get("sub_queries") if use_multi_query else None
        expected = set(item["expected_doc_ids"])

        t0 = time.perf_counter()
        results = service.search(query=query, top_k=top_k, sub_queries=sub_queries)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies_ms.append(elapsed_ms)

        retrieved_doc_ids = [r.doc_id for r in results]

        # Calculate rank of first matching doc
        first_match_rank = None
        for rank, r in enumerate(results, start=1):
            if r.doc_id in expected:
                first_match_rank = rank
                break

        hit = first_match_rank is not None
        if hit:
            recall_hits += 1
            rr = 1.0 / first_match_rank  # type: ignore
        else:
            rr = 0.0

        reciprocal_ranks.append(rr)

        query_reports.append(
            {
                "id": qid,
                "query": query,
                "category": item.get("category", "generic"),
                "expected": list(expected),
                "retrieved": retrieved_doc_ids,
                "hit": hit,
                "first_match_rank": first_match_rank,
                "latency_ms": round(elapsed_ms, 2),
                "top_score": results[0].score if results else 0.0,
            }
        )

    # Evaluate out of scope queries
    for item in out_of_scope_queries:
        t0 = time.perf_counter()
        results = service.search(query=item["query"], top_k=top_k)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies_ms.append(elapsed_ms)

    total_in_scope = len(in_scope_queries)
    recall_at_k = (recall_hits / total_in_scope) if total_in_scope > 0 else 0.0
    mrr_at_k = (statistics.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0

    p50_latency = statistics.median(latencies_ms) if latencies_ms else 0.0
    p95_latency = statistics.quantiles(latencies_ms, n=20)[18] if len(latencies_ms) >= 20 else max(latencies_ms)
    mean_latency = statistics.mean(latencies_ms) if latencies_ms else 0.0

    summary = {
        "total_queries": len(dataset),
        "in_scope_queries": total_in_scope,
        "out_of_scope_queries": len(out_of_scope_queries),
        "top_k": top_k,
        "multi_query_enabled": use_multi_query,
        "recall_at_5": round(recall_at_k, 4),
        "recall_percentage": f"{recall_at_k * 100:.1f}%",
        "mrr_at_5": round(mrr_at_k, 4),
        "latency_ms": {
            "mean": round(mean_latency, 2),
            "median_p50": round(p50_latency, 2),
            "p95": round(p95_latency, 2),
            "min": round(min(latencies_ms), 2) if latencies_ms else 0.0,
            "max": round(max(latencies_ms), 2) if latencies_ms else 0.0,
        },
        "query_details": query_reports,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Service Desk RAG Performance")
    parser.add_argument(
        "--dataset",
        type=str,
        default="backend/scripts/eval_dataset.json",
        help="Path to evaluation JSON dataset",
    )
    parser.add_argument(
        "--kb-dir",
        type=str,
        default="knowledge_base",
        help="Path to Markdown knowledge base",
    )
    parser.add_argument(
        "--persist-dir",
        type=str,
        default="./data/chroma_db",
        help="Path to ChromaDB persist dir",
    )
    parser.add_argument(
        "--fake-encoder",
        action="store_true",
        help="Use DeterministicFakeEncoder (runs completely offline in milliseconds)",
    )
    parser.add_argument(
        "--auto-index",
        action="store_true",
        help="Automatically index documents before running benchmark",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-K evaluation cutoff (default: 5)",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional path to write evaluation results JSON",
    )

    args = parser.parse_args()
    settings = get_settings()

    dataset_path = Path(args.dataset)
    kb_dir = Path(args.kb_dir)
    persist_dir = Path(args.persist_dir)

    if not dataset_path.exists():
        logger.error("Dataset not found: %s", dataset_path)
        sys.exit(1)

    encoder: BaseEmbeddingEncoder
    if args.fake_encoder or settings.RAG_USE_FAKE_ENCODER:
        logger.info("Evaluation using DeterministicFakeEncoder (deterministic offline mode)")
        encoder = DeterministicFakeEncoder(dimension=1024)
    else:
        logger.info("Evaluation using BGEM3Encoder (model=%s)", settings.EMBEDDING_MODEL_NAME)
        encoder = BGEM3Encoder(
            model_name=settings.EMBEDDING_MODEL_NAME,
            device=settings.EMBEDDING_DEVICE,
        )

    vector_store = ChromaVectorStore(
        persist_dir=persist_dir,
        model_name=encoder.model_name,
        dimension=encoder.dimension,
    )

    service = KnowledgeRetrievalService(
        encoder=encoder,
        vector_store=vector_store,
        base_kb_dir=kb_dir,
    )

    if args.auto_index or vector_store.count_chunks() == 0:
        logger.info("Indexing knowledge base before evaluation...")
        summary = service.index_documents(docs_dir=kb_dir, clean_obsolete=True)
        logger.info("Indexing completed: %d chunks created", summary.chunks_created)

    results = run_evaluation(
        dataset_path=dataset_path,
        service=service,
        top_k=args.top_k,
        use_multi_query=True,
    )

    print("\n" + "=" * 70)
    print("SERVICE DESK RAG EVALUATION BENCHMARK RESULTS")
    print("=" * 70)
    print(f"Embedding Model:         {encoder.model_name} ({encoder.dimension} dims)")
    print(f"Total Evaluated Queries: {results['total_queries']} ({results['in_scope_queries']} in-scope)")
    print(f"Recall@5:                {results['recall_percentage']} ({results['recall_at_5']})")
    print(f"MRR@5:                   {results['mrr_at_5']:.4f}")
    print(f"Mean Latency:            {results['latency_ms']['mean']:.2f} ms")
    print(f"P50 (Median) Latency:    {results['latency_ms']['median_p50']:.2f} ms")
    print(f"P95 Latency:             {results['latency_ms']['p95']:.2f} ms")
    print("=" * 70)

    print("\nDetailed Query Results:")
    print(f"{'ID':<5} {'Status':<6} {'Rank':<6} {'Latency':<10} {'Query'[:40]}")
    print("-" * 70)
    for q in results["query_details"]:
        status_str = "HIT" if q["hit"] else "MISS"
        rank_str = str(q["first_match_rank"]) if q["first_match_rank"] else "-"
        print(f"{q['id']:<5} {status_str:<6} {rank_str:<6} {q['latency_ms']:<8.2f}ms {q['query'][:38]}")
    print("-" * 70 + "\n")

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info("Results saved to %s", out_path)


if __name__ == "__main__":
    main()
