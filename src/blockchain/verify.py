"""
FaceTrace - Phase 7: On-Chain Verification
Independently re-verifies a saved evidence record against its blockchain
record, detecting whether the evidence has been tampered with since upload.
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.crypto.fingerprint import generate_fingerprint
from src.blockchain.chain_client import ChainClient


class VerificationError(Exception):
    pass


def verify_evidence(evidence_file_path: str, chain_upload_file_path: str = "data/evidence/last_chain_upload.json") -> dict:
    """
    Verifies that a saved evidence file's fingerprint matches what was
    stored on the blockchain.

    NOTE: because our local eth-tester chain is in-process and does not persist
    across script runs, this function re-deploys a fresh contract and re-uploads
    the ORIGINAL on-chain fingerprint (read from chain_upload_file_path, which
    recorded what was actually stored at upload time) purely to demonstrate the
    read-back and comparison mechanism. In a persistent/public chain deployment,
    this step would instead connect to the EXISTING deployed contract and read
    the EXISTING record directly - no re-upload needed. This distinction is
    documented in the README as a known limitation of the local-chain approach.

    Returns:
        dict with keys: verified (bool), local_fingerprint, onchain_fingerprint, details
    """
    if not os.path.exists(evidence_file_path):
        raise FileNotFoundError(f"Evidence file not found: {evidence_file_path}")

    if not os.path.exists(chain_upload_file_path):
        raise FileNotFoundError(
            f"Chain upload record not found: {chain_upload_file_path}. "
            f"Run chain_client.py first to upload a record."
        )

    with open(evidence_file_path, "r", encoding="utf-8") as f:
        evidence_file = json.load(f)

    with open(chain_upload_file_path, "r", encoding="utf-8") as f:
        chain_upload = json.load(f)

    original_onchain_fingerprint = chain_upload["fingerprint"]

    # Step 1: Recompute the fingerprint from the CURRENT state of the evidence record
    # (this is what would change if someone tampered with the evidence file)
    current_record = evidence_file["evidence_record"]
    recomputed_fingerprint = generate_fingerprint(current_record)

    # Step 2: Re-deploy chain and re-store the ORIGINAL on-chain fingerprint,
    # then read it back - simulating "the blockchain record as it was at upload time"
    client = ChainClient()
    client.deploy()
    upload_result = client.store_record(
        fingerprint=original_onchain_fingerprint,
        matched_post_url=chain_upload["matched_post_url"],
    )
    onchain_record = client.get_record(upload_result["record_id"])
    onchain_fingerprint = onchain_record["fingerprint"]

    # Step 3: Compare
    verified = (recomputed_fingerprint == onchain_fingerprint)

    return {
        "verified": verified,
        "local_recomputed_fingerprint": recomputed_fingerprint,
        "onchain_fingerprint": onchain_fingerprint,
        "evidence_file": evidence_file_path,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python src/blockchain/verify.py <path_to_evidence_json>")
        sys.exit(1)

    evidence_path = sys.argv[1]

    print(f"Verifying evidence file: {evidence_path}")
    print("Recomputing fingerprint from current evidence data...")
    print("Reading fingerprint from blockchain record...\n")

    result = verify_evidence(evidence_path)

    print(f"Recomputed fingerprint: {result['local_recomputed_fingerprint']}")
    print(f"On-chain fingerprint:   {result['onchain_fingerprint']}")
    print()

    if result["verified"]:
        print("VERIFICATION RESULT: AUTHENTIC - data is unmodified since blockchain upload.")
    else:
        print("VERIFICATION RESULT: TAMPERED - data does NOT match the blockchain record!")
        print("This means the evidence file has been altered since it was originally uploaded.")