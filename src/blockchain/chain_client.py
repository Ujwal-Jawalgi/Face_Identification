"""
FaceTrace - Phase 6: Blockchain Upload
Deploys a Solidity contract to a local, in-process Ethereum-compatible chain
(via eth-tester) and provides functions to store and retrieve fingerprint
records with real transactions.
"""

import os
import solcx
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

CONTRACT_PATH = os.path.join(os.path.dirname(__file__), "contract", "FaceTraceRegistry.sol")

# We point directly at a known-working manually-installed solc binary rather
# than relying on solcx's automatic version-lookup (get_executable), which has
# a known path-resolution bug on some Windows setups even when the binary
# itself is confirmed to work correctly via direct subprocess execution.
SOLC_BINARY_PATH = os.path.join(os.path.expanduser("~"), ".solcx", "solc-v0.8.19")


def _compile_contract():
    with open(CONTRACT_PATH, "r") as f:
        source = f.read()

    compiled = solcx.compile_source(
        source,
        output_values=["abi", "bin"],
        solc_binary=SOLC_BINARY_PATH,
    )

    contract_id, contract_interface = list(compiled.items())[0]
    return contract_interface["abi"], contract_interface["bin"]


class ChainClient:
    """
    Wraps a local, in-process Ethereum-compatible chain (eth-tester).
    Each new ChainClient() instance is a fresh chain - state does not
    persist across Python process restarts. This is expected and
    documented behavior for our local/simulated blockchain approach.
    """

    def __init__(self):
        self.w3 = Web3(EthereumTesterProvider())
        self.account = self.w3.eth.accounts[0]
        self.abi, self.bytecode = _compile_contract()
        self.contract_address = None
        self.contract = None

    def deploy(self):
        Contract = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        tx_hash = Contract.constructor().transact({"from": self.account})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.contract_address = tx_receipt.contractAddress
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)
        return self.contract_address

    def store_record(self, fingerprint, matched_post_url):
        if self.contract is None:
            raise RuntimeError("Contract not deployed yet. Call deploy() first.")

        tx_hash = self.contract.functions.storeRecord(
            fingerprint, matched_post_url
        ).transact({"from": self.account})

        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        logs = self.contract.events.RecordStored().process_receipt(tx_receipt)
        record_id = logs[0]["args"]["recordId"] if logs else None

        return {
            "record_id": record_id,
            "tx_hash": tx_hash.hex(),
            "block_number": tx_receipt.blockNumber,
            "gas_used": tx_receipt.gasUsed,
            "contract_address": self.contract_address,
        }

    def get_record(self, record_id):
        if self.contract is None:
            raise RuntimeError("Contract not deployed yet. Call deploy() first.")

        fingerprint, matched_post_url, timestamp, submitter = self.contract.functions.getRecord(record_id).call()

        return {
            "fingerprint": fingerprint,
            "matched_post_url": matched_post_url,
            "timestamp": timestamp,
            "submitter": submitter,
        }


if __name__ == "__main__":
    import sys
    import json

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.face.detect_encode import detect_and_encode
    from src.search.reverse_image_search import search_by_image
    from src.discovery.select_match import validate_and_select_match
    from src.crypto.fingerprint import build_evidence_record, generate_fingerprint, save_evidence

    if len(sys.argv) < 2:
        print("Usage: python src/blockchain/chain_client.py <path_to_image>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("Step 1-4: Running detection, search, validation, fingerprinting...")
    face_result = detect_and_encode(image_path)
    search_results = search_by_image(image_path)
    outcome = validate_and_select_match(face_result["embedding"], search_results)

    if not outcome["verified"]:
        print("No verified match found. Cannot proceed to blockchain upload.")
        sys.exit(1)

    match = outcome["best_match"]
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
    print(f"Fingerprint: {fingerprint}")
    print(f"Evidence saved to: {evidence_path}")

    print("\nStep 5: Deploying contract and uploading to blockchain...")
    client = ChainClient()
    address = client.deploy()
    print(f"Contract deployed at: {address}")

    result = client.store_record(fingerprint=fingerprint, matched_post_url=match["link"])
    print(f"\nRecord stored on-chain:")
    print(f"  Record ID: {result['record_id']}")
    print(f"  Transaction hash: {result['tx_hash']}")
    print(f"  Block number: {result['block_number']}")
    print(f"  Gas used: {result['gas_used']}")

    print("\nStep 6: Reading record back from chain to confirm...")
    onchain_record = client.get_record(result["record_id"])
    print(f"On-chain fingerprint: {onchain_record['fingerprint']}")

    assert onchain_record["fingerprint"] == fingerprint
    print("\nSUCCESS: On-chain fingerprint matches locally generated fingerprint.")

    # Save the on-chain result alongside the evidence for Phase 7 verification
    result["evidence_file"] = evidence_path
    result["fingerprint"] = fingerprint
    result["matched_post_url"] = match["link"]
    with open("data/evidence/last_chain_upload.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nChain upload details saved to: data/evidence/last_chain_upload.json")