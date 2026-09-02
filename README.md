# FaceTrace — Face Identification & Blockchain Verification

**Author:** Ujwal U

An end-to-end pipeline that takes a face image, finds a genuine, live-discovered matching post on the web/social media, cryptographically fingerprints the discovery, and records that fingerprint on a blockchain — enabling later verification of whether the discovered data is authentic or has been tampered with.

Built for HH Goa 2026 Shortlisting Task 3.

---

## Pipeline Overview

```
Face Image
    │
    ▼
[1] Face Detection & Encoding        (RetinaFace detector + Facenet embedding, via DeepFace)
    │
    ▼
[2] Genuine Live Web/Social Search   (SerpApi — Google Lens engine; zero hardcoded results)
    │
    ▼
[3] Match Validation                 (Independent face-embedding comparison — not just
    │                                  trusting the search engine's visual-similarity ranking)
    ▼
[4] Cryptographic Fingerprint        (SHA-256 over a canonical JSON evidence record)
    │
    ▼
[5] Blockchain Upload                (Local Ethereum-compatible chain via web3.py + eth-tester;
    │                                  real smart contract, real transaction, real gas cost)
    ▼
[6] On-Chain Verification            (Re-hash evidence, compare against on-chain record →
                                       AUTHENTIC or TAMPERED)
```

---

## Why This Design

### Reverse image search, not "PimEyes-style" face search across social media

A tool that can take a stranger's face and instantly find every place they've ever appeared on Instagram/Facebook/X would require a pre-built index of billions of already-scraped faces (what PimEyes/Clearview AI do). That's not buildable in this timeframe, isn't free, and scraping social platforms directly would violate their Terms of Service and this project's own stated ethics constraints.

Instead, this project uses **genuine reverse image search** (Google Lens via SerpApi): given an image, it live-searches the web and social platforms for pages where that same or a visually similar image already appears. This is a real, dynamic, non-hardcoded search — it only works if the specific image (or a near-duplicate) is already indexed somewhere public online. This is an honest and defensible interpretation of the task's requirement to find "a real matching social media post" via "reverse image search, an API, or a scripted search approach."

### Independent match validation (not just trusting the search engine)

During development, we found that Google Lens/SerpApi's visual-similarity ranking is **not** a reliable proxy for "same person." For an average, non-famous face, the top-ranked "visual match" was frequently a completely different, unrelated person who merely shared similar photo composition, clothing style, or background. See `docs/development-notes.md`-style detail in Known Limitations below.

To address this, every candidate result is independently re-validated: its thumbnail is downloaded, run through the same face-encoding pipeline used on the input image, and compared via cosine distance. Only candidates below a strict similarity threshold (0.40, DeepFace's documented Facenet verification threshold) are accepted as genuine matches — even if SerpApi ranked them #1. This is what makes the "matching post" claim actually trustworthy.

### Local blockchain, not a public testnet

We use `web3.py` + `eth-tester` — a real, in-process Ethereum Virtual Machine. It produces genuine transactions, gas costs, block numbers, and contract state; it is not a fake or simulated ledger. We chose this over a public testnet (e.g., Sepolia) for reliability during development and demonstration: no faucet dependency, no RPC provider account, no network flakiness risk during a live recording. The trade-off (documented below) is that state does not persist across process restarts.

---

## Technology Stack

| Component | Technology |
|---|---|
| Face detection | RetinaFace (via DeepFace) |
| Face encoding | Facenet (128-d embeddings, via DeepFace) |
| Reverse image search | SerpApi — Google Lens engine |
| Match validation | Cosine distance between Facenet embeddings |
| Hashing | SHA-256 (Python `hashlib`) over canonical JSON |
| Blockchain | Solidity smart contract on a local EVM (`web3.py` + `eth-tester`) |
| Compiler | `py-solc-x` (solc 0.8.19, manually resolved — see Known Limitations) |

---

## Project Structure

```
facetrace/
├── .env.example
├── requirements.txt
├── README.md
├── data/
│   ├── input/           # source face images
│   └── evidence/        # generated crops, evidence JSON, chain upload records
├── src/
│   ├── face/
│   │   └── detect_encode.py       # Face detection & encoding
│   ├── search/
│   │   └── reverse_image_search.py  # Genuine SerpApi/Google Lens search
│   ├── discovery/
│   │   └── select_match.py        # Independent embedding-based match validation
│   ├── crypto/
│   │   └── fingerprint.py         # Canonical evidence record + SHA-256 fingerprint
│   ├── blockchain/
│   │   ├── contract/
│   │   │   └── FaceTraceRegistry.sol
│   │   ├── chain_client.py        # Deploy contract, store/read records
│   │   └── verify.py              # Re-verification & tamper detection
│   └── pipeline.py                # Single-command end-to-end orchestrator
└── tests/
    └── test_face.py
```

---

## Setup

### Prerequisites
- Python 3.11+
- A free SerpApi account (serpapi.com) — 100 searches/month free tier

### Installation

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install tf-keras==2.16.0
```

### Configuration

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set your real SerpApi key:
```
SERPAPI_API_KEY=your_real_key_here
```

### Solidity compiler (solc) — manual step required on some networks

If `pip install` and normal operation succeed but the blockchain step fails to reach `solc-bin.ethereum.org`, your network may be blocking that specific domain (observed during development — see Known Limitations). Workaround:

1. Download `https://github.com/ethereum/solidity/releases/download/v0.8.19/solc-windows.exe` manually via browser (GitHub is typically unblocked even when `ethereum.org` is not).
2. Place it at `%USERPROFILE%\.solcx\solc-v0.8.19` (no file extension).
3. `Unblock-File` on it if Windows flags it as downloaded-from-internet.

---

## Running the Pipeline

### Full end-to-end run

```powershell
python -m src.pipeline "data/input/your_face_image.jpg"
```

This runs all 6 pipeline stages in one command and prints a sectioned, demo-ready log ending in a final verified/mismatch result. It also writes:
- `data/evidence/evidence_<timestamp>.json` — the full evidence record + fingerprint
- `data/evidence/last_chain_upload.json` — the on-chain transaction summary

### Verification / tamper-detection demo

```powershell
python src/blockchain/verify.py "data/evidence/evidence_<timestamp>.json"
```

This recomputes the fingerprint from the current evidence file and compares it against the on-chain record.

- Run it unmodified → **AUTHENTIC**
- Copy the evidence file, edit any field (e.g., the matched URL or distance score), then run it against the copy → **TAMPERED**

This is the clearest demonstration that the blockchain record is doing real integrity-checking work, not acting as decoration.

### Individual stage testing (useful for development/debugging)

```powershell
python src/face/detect_encode.py "data/input/your_image.jpg"
python src/search/reverse_image_search.py "data/input/your_image.jpg"
python src/discovery/select_match.py "data/input/your_image.jpg"
python src/crypto/fingerprint.py "data/input/your_image.jpg"
python src/blockchain/chain_client.py
```

---

## Verification Methodology

1. At upload time, a canonical JSON evidence record is built containing: a SHA-256 hash of the source image, a SHA-256 hash of the face embedding (rounded to fixed precision for determinism), the discovered match's title/link/source/similarity-distance, and a UTC timestamp.
2. That record is serialized deterministically (sorted keys, fixed separators) and SHA-256 hashed to produce the final fingerprint.
3. The fingerprint (not the full record — keeping on-chain storage minimal) is written to a smart contract via a real transaction.
4. To verify later: re-load the saved evidence JSON, recompute its fingerprint from its *current* contents, and compare against the fingerprint read back from the chain.
5. Any change to the evidence file — even a single character — produces a completely different SHA-256 hash, causing verification to report **TAMPERED**.

**Important limitation on the local chain:** because `eth-tester` runs in-process and does not persist state across script restarts, `verify.py` re-deploys a fresh contract and re-uploads the *original* on-chain fingerprint (read from the saved `last_chain_upload.json`) purely to demonstrate the read-back/comparison mechanism. On a persistent chain (a real node, or a public testnet), this step would instead connect to the *existing* deployed contract and read the *existing* record directly, with no re-upload needed. The comparison logic itself (recompute vs. on-chain value) is identical either way — only the "how do I reach the chain" plumbing differs.

---

## Known Limitations (Honest Assessment)

- **Reverse image search only finds already-indexed images.** If a face photo has never been posted publicly anywhere Google has crawled, the search will correctly return no verified match — this is expected behavior, not a bug. Public figures and well-indexed profile photos (LinkedIn, X, Pinterest) work reliably; Instagram and Facebook posts are poorly indexed by Google due to those platforms' `robots.txt` restrictions, and are much less likely to surface.
- **Google Lens' visual-similarity ranking is not identity-verification.** During development, unvalidated top search results frequently turned out to be different, unrelated people who merely shared similar photo composition. This project's independent embedding-comparison step (Phase 4) exists specifically to correct for this; without it, the "matching post" claim would not be trustworthy.
- **Local blockchain does not persist across process restarts.** `eth-tester` is a genuine in-process EVM, not a fake ledger — but its state lives only for the duration of one Python process. A production deployment would target a persistent node or public testnet instead.
- **`solc-bin.ethereum.org` was blocked on the development network**, requiring a manual workaround (downloading the Windows solc binary directly from GitHub and pointing `solcx` at it explicitly via `solc_binary=`) due to an unrelated bug in `py-solc-x`'s own Windows executable-path resolution.
- **SerpApi free tier is capped at 100 searches/month.** Each full pipeline run and each individual `search_by_image()` call consumes one search credit.
- **Face detection can occasionally false-positive on generic detector backends.** This project uses RetinaFace (not the faster but less accurate OpenCV Haar cascade default) specifically because the latter was observed misidentifying background textures (foliage, fabric patterns) as faces during testing.

---

## What a Demo Recording Should Show

1. `python -m src.pipeline "data/input/<image>.jpg"` — full run, live search, verified match, real blockchain transaction
2. Briefly open the matched post's real URL in a browser to confirm it genuinely exists
3. `python src/blockchain/verify.py "<evidence_file>"` on the unmodified evidence → **AUTHENTIC**
4. Copy the evidence file, edit one field, re-run verify on the copy → **TAMPERED**