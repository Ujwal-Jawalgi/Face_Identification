"""
FaceTrace - Phase 4: Matching Post Discovery & Validation
Takes raw SerpApi visual_matches and independently verifies which ones
are actually the same person, using our own face embedding comparison
(not just trusting Google Lens's visual-similarity ranking).
"""

import os
import io
import tempfile
import numpy as np
import requests
from deepface import DeepFace

# Facenet's standard verification threshold (cosine distance).
# Below this = same person. Above = different person.
# This is DeepFace's documented default for the Facenet model.
FACE_MATCH_THRESHOLD = 0.40

SOCIAL_DOMAINS = [
    "instagram.com", "facebook.com", "x.com", "twitter.com",
    "linkedin.com", "pinterest.com", "tiktok.com", "snapchat.com",
]


class MatchValidationError(Exception):
    pass


def _cosine_distance(emb1, emb2) -> float:
    emb1 = np.array(emb1)
    emb2 = np.array(emb2)
    cosine_similarity = np.dot(emb1, emb2) / (
        np.linalg.norm(emb1) * np.linalg.norm(emb2)
    )
    return 1 - cosine_similarity


def _download_image(url: str) -> str:
    """Downloads an image to a temp file, returns the local path."""
    response = requests.get(url, timeout=15)
    response.raise_for_status()

    suffix = ".jpg"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(response.content)
    tmp.close()
    return tmp.name


def _get_embedding_for_thumbnail(thumbnail_url: str):
    """Downloads a candidate's thumbnail and extracts its face embedding.
    Returns None if no face is detected or download fails."""
    local_path = None
    try:
        local_path = _download_image(thumbnail_url)
        results = DeepFace.represent(
            img_path=local_path,
            model_name="Facenet",
            enforce_detection=True,
            detector_backend="opencv",
        )
        return results[0]["embedding"]
    except Exception:
        # No face found, broken image, network issue, etc. -> treat as unverifiable
        return None
    finally:
        if local_path and os.path.exists(local_path):
            os.remove(local_path)


def _is_social_platform(link: str) -> bool:
    return any(domain in (link or "") for domain in SOCIAL_DOMAINS)


def validate_and_select_match(input_embedding: list, raw_search_results: dict, max_candidates_to_check: int = 6) -> dict:
    """
    Independently verifies SerpApi visual_matches against the input face embedding.

    Args:
        input_embedding: the embedding from our own Phase 2 detect_and_encode() call.
        raw_search_results: the raw dict from search_by_image() (Phase 3).
        max_candidates_to_check: limits how many candidates we download/verify,
            to control time and bandwidth (checking all 60 isn't necessary).

    Returns:
        dict describing the outcome:
            {
              "verified": bool,
              "best_match": {...} or None,
              "distance": float or None,
              "checked_count": int,
              "all_candidates_checked": [...]   # for transparency/debugging
            }
    """
    visual_matches = raw_search_results.get("visual_matches", [])[:max_candidates_to_check]

    checked = []
    verified_candidates = []

    for match in visual_matches:
        thumbnail = match.get("thumbnail")
        if not thumbnail:
            continue

        candidate_embedding = _get_embedding_for_thumbnail(thumbnail)

        entry = {
            "title": match.get("title"),
            "link": match.get("link"),
            "source": match.get("source"),
            "thumbnail": match.get("thumbnail"),
            "image": match.get("image"),
            "snippet": match.get("snippet"),
            "is_social_platform": _is_social_platform(match.get("link")),
            "face_detected": candidate_embedding is not None,
            "distance": None,
        }

        if candidate_embedding is not None:
            distance = _cosine_distance(input_embedding, candidate_embedding)
            entry["distance"] = float(distance)
            # Honest, directly-derived confidence percentage from the real distance
            # score (0 distance = 100% confidence, higher distance = lower confidence).
            # This is a transparent transformation of our validated metric, not a
            # separately trained or fabricated score.
            confidence = max(0.0, min(1.0, 1 - distance)) * 100
            entry["confidence_percent"] = round(confidence, 1)
            if distance <= FACE_MATCH_THRESHOLD:
                verified_candidates.append(entry)

        checked.append(entry)

    if not verified_candidates:
        return {
            "verified": False,
            "best_match": None,
            "distance": None,
            "checked_count": len(checked),
            "all_candidates_checked": checked,
        }

    # Prefer social-platform matches among verified candidates; break ties by lowest distance
    verified_candidates.sort(
        key=lambda c: (not c["is_social_platform"], c["distance"])
    )

    best = verified_candidates[0]

    return {
        "verified": True,
        "best_match": best,
        "distance": best["distance"],
        "checked_count": len(checked),
        "all_candidates_checked": checked,
    }


if __name__ == "__main__":
    import sys
    import json
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.face.detect_encode import detect_and_encode
    from src.search.reverse_image_search import search_by_image

    if len(sys.argv) < 2:
        print("Usage: python src/discovery/select_match.py <path_to_image>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("Step 1: Detecting and encoding face...")
    face_result = detect_and_encode(image_path)
    print(f"  Embedding dimension: {face_result['embedding_dim']}")

    print("\nStep 2: Performing live reverse image search...")
    search_results = search_by_image(image_path)
    print(f"  Raw matches returned: {len(search_results.get('visual_matches', []))}")

    print("\nStep 3: Independently validating candidates against face embedding...")
    outcome = validate_and_select_match(face_result["embedding"], search_results)

    print(f"\nChecked {outcome['checked_count']} candidates (with detectable faces).")
    print("\n--- Validation details ---")
    for c in outcome["all_candidates_checked"]:
        status = "FACE NOT FOUND" if not c["face_detected"] else f"distance={c['distance']:.4f}"
        print(f"  [{status}] {c['source']}: {c['title']}")

    print("\n--- Final Result ---")
    if outcome["verified"]:
        m = outcome["best_match"]
        print(f"VERIFIED MATCH FOUND (distance={m['distance']:.4f}, threshold={FACE_MATCH_THRESHOLD})")
        print(f"Title:  {m['title']}")
        print(f"Link:   {m['link']}")
        print(f"Source: {m['source']}")
    else:
        print("NO VERIFIED MATCH — no candidate passed the face-similarity threshold.")
        print("This means the search found visually similar images, but none were")
        print("confirmed to be the same face by independent embedding comparison.")