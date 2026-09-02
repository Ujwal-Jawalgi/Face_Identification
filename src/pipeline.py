"""
FaceTrace - Phase 8: End-to-End Pipeline
Single entrypoint that runs the complete flow:
Face Image -> Detection & Encoding -> Genuine Search -> Match Validation
-> Cryptographic Fingerprint -> Blockchain Upload -> On-Chain Confirmation
"""

import os
import sys
import json

from src.face.detect_encode import detect_and_encode, FaceDetectionError
from src.search.reverse_image_search import search_by_image, SerpApiError
from src.discovery.select_match import validate_and_select_match
from src.crypto.fingerprint import build_evidence_record, generate_fingerprint, save_evidence
from src.blockchain.chain_client import ChainClient


def _section(title: str):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def run_pipeline(image_path: str) -> dict:
    """
    Runs the full FaceTrace pipeline on the given image.
    Returns a summary dict of the final result, or raises on unrecoverable failure.
    """

    if not os.path.exists(image_path):
        print(f"ERROR: Input image not found: {image_path}")
        sys.exit(1)

    _section("STEP 1-2: FACE DETECTION & ENCODING")
    print(f"Input image: {image_path}")
    try:
        face_result = detect_and_encode(image_path)
    except FaceDetectionError as e:
        print(f"FAILED: {e}")
        sys.exit(1)

    print(f"Face detected successfully.")
    print(f"  Model: {face_result['embedding_model']}")
    print(f"  Embedding dimension: {face_result['embedding_dim']}")
    print(f"  Cropped face saved to: {face_result['cropped_face_path']}")

    _section("STEP 3: GENUINE LIVE WEB/SOCIAL MEDIA SEARCH")
    print("Searching live via SerpApi (Google Lens engine) - no hardcoded results...")
    try:
        search_results = search_by_image(image_path)
    except SerpApiError as e:
        print(f"FAILED: {e}")
        sys.exit(1)

    total_matches = len(search_results.get("visual_matches", []))
    print(f"Search completed. {total_matches} raw visual matches returned live.")

    _section("STEP 4: MATCHING POST VALIDATION")
    print("Independently verifying candidates against face embedding")
    print("(not trusting search engine ranking alone)...")
    outcome = validate_and_select_match(face_result["embedding"], search_results)

    print(f"Checked {outcome['checked_count']} candidates with detectable faces.")

    if not outcome["verified"]:
        print("\nNO VERIFIED MATCH FOUND.")
        print("The search found visually similar images, but none were confirmed")
        print("to be the same face via independent embedding comparison.")
        print("Pipeline cannot proceed to fingerprinting/blockchain without a genuine match.")
        sys.exit(1)

    match = outcome["best_match"]
    print(f"\nVERIFIED MATCH FOUND:")
    print(f"  Title:  {match['title']}")
    print(f"  Link:   {match['link']}")
    print(f"  Source: {match['source']}")
    print(f"  Face similarity distance: {match['distance']:.4f} (threshold: 0.40)")

    _section("STEP 5: CRYPTOGRAPHIC FINGERPRINTING")
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
    evidence_path = save_evidence(record, fingerprint)

    print(f"Evidence record built (image hash, embedding hash, match data, timestamp).")
    print(f"SHA-256 Fingerprint: {fingerprint}")
    print(f"Evidence saved to: {evidence_path}")

    _section("STEP 6: BLOCKCHAIN UPLOAD")
    print("Deploying smart contract to local Ethereum-compatible chain...")
    client = ChainClient()
    contract_address = client.deploy()
    print(f"Contract deployed at: {contract_address}")

    print("Storing fingerprint on-chain via real transaction...")
    upload_result = client.store_record(fingerprint=fingerprint, matched_post_url=match["link"])
    print(f"  Record ID: {upload_result['record_id']}")
    print(f"  Transaction hash: {upload_result['tx_hash']}")
    print(f"  Block number: {upload_result['block_number']}")
    print(f"  Gas used: {upload_result['gas_used']}")

    _section("STEP 7: ON-CHAIN VERIFICATION")
    onchain_record = client.get_record(upload_result["record_id"])
    match_ok = (onchain_record["fingerprint"] == fingerprint)

    print(f"Local fingerprint:   {fingerprint}")
    print(f"On-chain fingerprint: {onchain_record['fingerprint']}")

    _section("FINAL RESULT")
    if match_ok:
        print("VERIFIED: The discovered post's fingerprint has been successfully")
        print("recorded on the blockchain and matches on independent read-back.")
        print(f"\nMatched post: {match['link']}")
    else:
        print("MISMATCH: something went wrong - on-chain data does not match.")

    # Save full run summary for later reference / Phase 7 tamper-demo script
    summary = {
        "image_path": image_path,
        "matched_post": match,
        "fingerprint": fingerprint,
        "evidence_file": evidence_path,
        "contract_address": contract_address,
        "tx_hash": upload_result["tx_hash"],
        "record_id": upload_result["record_id"],
        "matched_post_url": match["link"],
        "block_number": upload_result["block_number"],
        "gas_used": upload_result["gas_used"],
        "verified_on_chain": match_ok,
    }

    with open("data/evidence/last_chain_upload.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline <path_to_image>")
        sys.exit(1)

    run_pipeline(sys.argv[1])