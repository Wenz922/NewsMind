import json
import numpy as np
from functools import lru_cache
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_model():
    """
    Load the MiniLM-L6 embedding model only once.
    Prevents repeated heavy initialization.
    """
    return SentenceTransformer("all-MiniLM-L6-v2")


def generate_embedding(text: str) -> str:
    """
    Generate the embedding JSON string for a given text.
    Returns a JSON list of floats.
    """
    if not text or not text.strip():
        return json.dumps([])

    model = get_model()
    vector = model.encode(text).tolist()

    # Convert to JSON for DB storage
    return json.dumps(vector)


def compute_similarity(vec1: str, vec2: str) -> float:
    """
    Compute cosine similarity between two JSON embeddings.
    Safe fallback values for missing/invalid vectors.
    """
    try:
        v1 = np.array(json.loads(vec1))
        v2 = np.array(json.loads(vec2))

        if v1.size == 0 or v2.size == 0:
            return 0.0  # No embedding stored → no similarity

        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    except Exception as e:
        print(f"[Embedding Similarity Error] {e}")
        return 0.0
