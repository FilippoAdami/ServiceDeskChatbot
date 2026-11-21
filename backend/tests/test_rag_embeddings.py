import math

from backend.app.rag.embeddings.fake import DeterministicFakeEncoder


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0


def test_fake_encoder_determinism_and_dimensions() -> None:
    encoder = DeterministicFakeEncoder(dimension=1024)
    assert encoder.dimension == 1024
    assert encoder.model_name == "fake-bge-m3-deterministic"

    text = "Procedura di reset password aziendale"
    vec1 = encoder.encode_documents([text])[0]
    vec2 = encoder.encode_documents([text])[0]

    assert len(vec1) == 1024
    assert vec1 == vec2  # Perfectly deterministic

    norm = math.sqrt(sum(x * x for x in vec1))
    assert math.isclose(norm, 1.0, rel_tol=1e-5)


def test_fake_encoder_semantic_overlap() -> None:
    encoder = DeterministicFakeEncoder(dimension=1024)

    text_target = "Procedura di reset password e sblocco account"
    text_related = "Come posso reimpostare la mia password e sbloccare l'account?"
    text_unrelated = "Configurazione del server di stampa per brochure di marketing"

    vec_target = encoder.encode_documents([text_target])[0]
    vec_related = encoder.encode_queries([text_related])[0]
    vec_unrelated = encoder.encode_queries([text_unrelated])[0]

    sim_related = cosine_similarity(vec_target, vec_related)
    sim_unrelated = cosine_similarity(vec_target, vec_unrelated)

    assert sim_related > sim_unrelated
    assert sim_related > 0.4
