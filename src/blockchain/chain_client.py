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
    print("Deploying FaceTraceRegistry contract to local eth-tester chain...")
    client = ChainClient()
    address = client.deploy()
    print(f"Contract deployed at: {address}")

    print("\nStoring a test record...")
    result = client.store_record(
        fingerprint="test_fingerprint_1234567890abcdef",
        matched_post_url="https://example.com/test-post",
    )
    print(f"Record stored: {result}")

    print("\nReading the record back from chain...")
    record = client.get_record(result["record_id"])
    print(f"Retrieved record: {record}")

    assert record["fingerprint"] == "test_fingerprint_1234567890abcdef"
    print("\nVerification: stored and retrieved fingerprint match. Blockchain round-trip successful.")