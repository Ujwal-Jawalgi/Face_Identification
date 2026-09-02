"""
FaceTrace - Phase 5: Cryptographic Fingerprinting
Combines face encoding data + discovered match data into a canonical,
deterministic JSON structure, then generates a SHA-256 fingerprint of it.
"""

import os
import json
import hashlib
from datetime import datetime, timezone


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return _sha256_bytes(f.read())


def _sha256_embedding(embedding: list) -> str:
    """
    Hashes an embedding vector deterministically by first rounding to a fixed
    precision (avoids floating-point representation differences across runs/
    systems) and serializing as a fixed-format string before hashing.
    """
    rounded = [round(float(x), 8) for x in embedding]
    serialized = ",".join(f"{x:.8f}" for x in rounded)
    return _sha256_bytes(serialized.encode("utf-8"))


def build_evidence_record(
    source_image_path: str,
    face_embedding: list,
    embedding_model: str,
    match_title: str,
    match_link: str,
    match_source: str,
    match_distance: float,
) -> dict:
    """
    Builds the full evidence record that will be hashed and stored on-chain.

    This is the "canonical" data structure - the same inputs will always
    produce the same structure, which is required for deterministic hashing.
    """
    image_hash = _sha256_file(source_image_path)
    embedding_hash = _sha256_embedding(face_embedding)

    record = {
        "source_image_hash": image_hash,
        "embedding_hash": embedding_hash,
        "embedding_model": embedding_model,
        "matched_post": {
            "title": match_title,
            "link": match_link,
            "source": match_source,
            "face_similarity_distance": round(float(match_distance), 4),
        },
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return record


def canonicalize(record: dict) -> str:
    """
    Serializes a dict into a canonical JSON string:
    sorted keys, fixed separators, no extra whitespace.
    This ensures the same data always produces byte-identical text.
    """
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def generate_fingerprint(record: dict) -> str:
    """
    Generates the final SHA-256 fingerprint hash of the evidence record.
    """
    canonical_str = canonicalize(record)
    return _sha256_bytes(canonical_str.encode("utf-8"))


def save_evidence(record: dict, fingerprint: str, output_dir: str = "data/evidence") -> str:
    """
    Saves the full evidence record + its fingerprint to a JSON file on disk.
    This file is what we'll re-hash later during verification (Phase 7) to
    detect tampering.
    """
    os.makedirs(output_dir, exist_ok=True)

    output = {
        "evidence_record": record,
        "fingerprint_sha256": fingerprint,
    }

    timestamp_safe = record["created_at_utc"].replace(":", "-")
    file_path = os.path.join(output_dir, f"evidence_{timestamp_safe}.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    return file_path


if __name__ == "__main__":
    # Manual test entrypoint - reuses Phase 2/3/4 to build a real record end to end
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.face.detect_encode import detect_and_encode
    from src.search.reverse_image_search import search_by_image
    from src.discovery.select_match import validate_and_select_match

    if len(sys.argv) < 2:
        print("Usage: python src/crypto/fingerprint.py <path_to_image>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("Step 1: Detecting and encoding face...")
    face_result = detect_and_encode(image_path)

    print("Step 2: Performing live reverse image search...")
    search_results = search_by_image(image_path)

    print("Step 3: Validating candidates...")
    outcome = validate_and_select_match(face_result["embedding"], search_results)

    if not outcome["verified"]:
        print("No verified match found - cannot build evidence record without a genuine match.")
        sys.exit(1)

    match = outcome["best_match"]
    print(f"Verified match: {match['title']} ({match['link']})")

    print("\nStep 4: Building evidence record and fingerprint...")
    record = build_evidence_record(
        source_image_path=image_path,
        face_embedding=face_result["embedding"],
        embedding_model=face_result["embedding_model"],
        match_title=match["title"],
        match_link=match["link"],
        match_source=match["source"],
        match_distance=match["distance"],
    )

    fingerprint = generate_fingerprint(record)
    saved_path = save_evidence(record, fingerprint)

    print(f"\nFingerprint (SHA-256): {fingerprint}")
    print(f"Evidence saved to: {saved_path}")