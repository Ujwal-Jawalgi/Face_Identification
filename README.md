# FaceTrace — Face Identification & Blockchain Verification

**Team:** Team Pikachu
**Team Members:** Ujwal U, Srilakshmi
**Contact:** ujwaljawalgi2208@gmail.com, dsrilakshmi@gmail.com

Built for **HH Goa 2026 Shortlisting Task 3: Face Identification & Blockchain Verification**.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [What This Project Does](#what-this-project-does)
3. [Architecture & Technology Choices](#architecture--technology-choices)
4. [Project Structure](#project-structure)
5. [How to Use This Project](#how-to-use-this-project)
6. [Pipeline Stage-by-Stage Breakdown](#pipeline-stage-by-stage-breakdown)
7. [Verification Methodology](#verification-methodology)
8. [Testing](#testing)
9. [Design Notes & Considerations](#design-notes--considerations)
10. [Troubleshooting](#troubleshooting)
11. [What the Demo Shows](#what-the-demo-shows)
12. [Contact](#contact)

---

## Problem Statement

Task 3 asks for a pipeline shaped as: **Face scan input → Web/social media search (find matching post) → Blockchain upload/verification of the discovered data**, with three hard requirements:

1. Genuine face detection and encoding (any library/API acceptable)
2. A **real, dynamic** web/social media search that finds an actual matching post — not a hardcoded or pre-picked result
3. Blockchain-based, tamper-evident verification of the discovered data, with the ability to demonstrate re-verifying it later

FaceTrace implements all three end to end, using entirely free/local tooling, with no public deployment required.

---

## What This Project Does

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

Given a face photo, FaceTrace:
1. Detects and encodes the face
2. Performs a **live, dynamic reverse-image search** across the web and social platforms — no hardcoded or pre-picked results
3. Independently re-verifies any candidate match is genuinely the same face (not just visually similar, which search engines alone cannot guarantee)
4. Builds a cryptographic fingerprint of the discovered evidence
5. Uploads that fingerprint to a blockchain via a real smart contract transaction
6. Can later re-verify the evidence against the blockchain record to prove it's authentic — or detect that it's been tampered with

A lightweight optional local web UI is also included for a more visual way to run and present the pipeline (not required by the task, but useful for demonstration).

---

## Architecture & Technology Choices

| Component | Technology | Why |
|---|---|---|
| Face detection | RetinaFace (via DeepFace) | Deep-learning-based detector; accurately localizes real faces and avoids false positives on busy backgrounds (an earlier OpenCV Haar-cascade attempt misidentified background textures as faces) |
| Face encoding | Facenet (128-d embeddings, via DeepFace) | Well-supported, widely-used embedding model for face comparison |
| Reverse image search | SerpApi — Google Lens engine | Official, legal API access to genuine reverse image search; free tier available (100 searches/month); no scraping or CAPTCHA-bypassing involved |
| Match validation | Cosine distance between Facenet embeddings | Ensures a "matching post" is independently verified as the same face, not just visually similar per the search engine's own ranking |
| Hashing | SHA-256 over canonical JSON | Standard, deterministic cryptographic fingerprinting |
| Blockchain | Local Ethereum-compatible chain (`web3.py` + `eth-tester`) | A genuine, real EVM — real smart contract deployment, real transactions, real gas costs — chosen for reliability during development and demonstration, per the task's explicit allowance for "local/simulated chain" |
| Smart contract compiler | `py-solc-x` (solc 0.8.19) | Pure-Python Solidity compilation, no Node.js/Hardhat/Truffle dependency |
| Optional UI | Flask + vanilla HTML/CSS/JS | A lightweight local web interface; no Node.js build step, kept strictly Python-based |

### Why reverse image search, not a "search any stranger's face across social media" tool

A tool that instantly finds every place a random stranger's face has appeared across Instagram/Facebook/X would require a pre-built index of billions of already-scraped faces (the approach used by tools like PimEyes/Clearview AI). That's not something buildable in a short timeframe, isn't free, and scraping social platforms directly would violate their Terms of Service. Instead, FaceTrace uses **genuine reverse image search**: given an image, it live-searches the web for pages where that same or a visually similar image already appears. This is a real, dynamic, non-hardcoded search step, matching the task's requirement for "a real matching social media post... via reverse image search, an API, or a scripted search approach."

### Why independent match validation matters

During development, we found that a search engine's visual-similarity ranking alone is not reliable proof of identity — for an average, non-famous face, the top-ranked result was sometimes a completely different, unrelated person who merely shared similar photo composition, clothing, or background. FaceTrace re-validates every candidate independently: downloading its thumbnail/image, running it through the same face-encoding pipeline used on the input, and only accepting matches below a strict, standard similarity threshold (0.40 cosine distance for Facenet). This is what makes the "matching post" claim genuinely trustworthy rather than simply trusting the search engine's opinion.

### Why a local blockchain rather than a public testnet

`eth-tester` gives a real, in-process Ethereum Virtual Machine — genuine transactions, gas costs, block numbers, and contract state, not a mock or fake ledger. We chose it over a public testnet (e.g., Sepolia) specifically for demonstration reliability: no dependency on a testnet faucet, no third-party RPC provider account, and no exposure to public network flakiness during a live recording. The one trade-off — state doesn't persist across process restarts — is documented below along with what would change to use a persistent chain instead.

---

## Project Structure

```
facetrace/
├── app.py                      # Optional local web UI (Flask)
├── templates/, static/         # Web UI frontend files
├── requirements.txt
├── .env.example
├── README.md
├── data/
│   ├── input/                  # source face images
│   └── evidence/                # generated crops, evidence JSON, chain upload records
├── src/
│   ├── face/
│   │   └── detect_encode.py            # Face detection & encoding
│   ├── search/
│   │   └── reverse_image_search.py     # Genuine SerpApi/Google Lens search
│   ├── discovery/
│   │   └── select_match.py             # Independent embedding-based match validation
│   ├── crypto/
│   │   └── fingerprint.py              # Canonical evidence record + SHA-256 fingerprint
│   ├── blockchain/
│   │   ├── contract/
│   │   │   └── FaceTraceRegistry.sol   # Solidity smart contract
│   │   ├── chain_client.py             # Deploy contract, store/read records
│   │   └── verify.py                   # Re-verification & tamper detection
│   └── pipeline.py                     # Single-command end-to-end orchestrator
└── tests/
    └── test_face.py
```

---

## How to Use This Project

### 1. Prerequisites
- Python 3.11+
- A free SerpApi account (serpapi.com) — 100 searches/month free tier, no credit card required

### 2. Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install tf-keras==2.16.0
```

### 3. Configure your API key

```powershell
Copy-Item .env.example .env
```
Edit `.env` and add your key:
```
SERPAPI_API_KEY=your_real_key_here
```

### 4. Solidity compiler note (Windows)

`py-solc-x` normally auto-downloads the Solidity compiler from `solc-bin.ethereum.org`. If your network blocks this domain:
1. Manually download `https://github.com/ethereum/solidity/releases/download/v0.8.19/solc-windows.exe`
2. Place it at `%USERPROFILE%\.solcx\solc-v0.8.19` (no file extension)
3. Run `Unblock-File "$env:USERPROFILE\.solcx\solc-v0.8.19"` if Windows flags it as downloaded content

### 5. Run the full pipeline (command line)

```powershell
python -m src.pipeline "data/input/your_face_image.jpg"
```
Runs all 6 stages in one command with clear, sectioned console output, ending in a verified result. Produces:
- `data/evidence/evidence_<timestamp>.json` — the full evidence record + fingerprint
- `data/evidence/last_chain_upload.json` — the on-chain transaction summary

### 6. Verify authenticity / demonstrate tamper detection

```powershell
python src/blockchain/verify.py "data/evidence/evidence_<timestamp>.json"
```
- Run unmodified → reports **AUTHENTIC**
- Copy the file, edit any field, run against the copy → reports **TAMPERED**

### 7. (Optional) Run the web UI

```powershell
python app.py
```
Open `http://localhost:5000`, upload a face image, click "Analyze Target."

---

## Pipeline Stage-by-Stage Breakdown

**Stage 1 — Face Detection & Encoding** (`src/face/detect_encode.py`)
Detects a face using RetinaFace, crops it (with padding for a natural-looking result), and generates a 128-dimensional Facenet embedding vector representing that face numerically.

**Stage 2 — Genuine Search** (`src/search/reverse_image_search.py`)
Uploads the image to SerpApi's Image API (compressing/resizing if needed to fit SerpApi's 500KB limit), then queries the Google Lens engine live. Returns real, unfiltered visual match candidates from across the web at request time — nothing pre-selected.

**Stage 3 — Match Validation** (`src/discovery/select_match.py`)
For each candidate (up to 15, to bound runtime), downloads its thumbnail/image, runs the same face-detection-and-encoding pipeline on it, and computes cosine distance against the input's embedding. Only candidates below the 0.40 threshold are accepted; among those, social-media-domain results are prioritized. Every candidate is also tagged with a directly-derived confidence percentage (`(1 - distance) × 100`).

**Stage 4 — Fingerprinting** (`src/crypto/fingerprint.py`)
Builds a canonical (sorted-key, fixed-format) JSON record containing the image's SHA-256 hash, the embedding's SHA-256 hash, and the matched post's metadata, then SHA-256 hashes that entire record to produce the final fingerprint.

**Stage 5 — Blockchain Upload** (`src/blockchain/chain_client.py`)
Compiles and deploys `FaceTraceRegistry.sol` to a local, in-process EVM, then calls `storeRecord()` with the fingerprint and matched post URL via a real transaction.

**Stage 6 — On-Chain Verification** (`src/blockchain/verify.py`)
Reads the stored record back from the contract and compares it against a freshly recomputed hash of the saved evidence file, reporting AUTHENTIC or TAMPERED.

---

## Verification Methodology

1. At upload time, a canonical JSON evidence record is built: a SHA-256 hash of the source image, a SHA-256 hash of the face embedding (rounded to fixed precision for reproducibility), the discovered match's title/link/source/similarity-distance, and a UTC timestamp.
2. That record is serialized deterministically (sorted keys, fixed separators) and SHA-256 hashed to produce the final fingerprint.
3. The fingerprint is written to a smart contract via a real transaction — keeping on-chain storage minimal and gas-efficient (raw evidence stays off-chain, only its hash is committed).
4. To verify later: reload the saved evidence JSON, recompute its fingerprint from its *current* contents, and compare against the fingerprint read back from the chain.
5. Any change to the evidence file — even a single character — produces a completely different SHA-256 hash (the avalanche effect of cryptographic hashing), so verification correctly reports **TAMPERED**.

**Note on the local chain:** because `eth-tester` runs in-process and doesn't persist state across script restarts, `verify.py` re-deploys a fresh contract and re-uploads the *original* on-chain fingerprint (read from `last_chain_upload.json`) to demonstrate the read-back/comparison mechanism cleanly and repeatably in one self-contained script. On a persistent node or public testnet, this same comparison logic would simply read the *existing* record directly from the *existing* contract — the underlying integrity check (recompute vs. on-chain value) is identical either way; only the "how do I reach the chain" plumbing differs.

---

## Testing

`tests/test_face.py` covers the face detection/encoding stage:
- Valid image → produces a correctly-shaped embedding and a saved cropped face file
- Same image run twice → produces identical embeddings (determinism check)
- No-face image → raises a clean `FaceDetectionError`, not a crash
- Missing file → raises `FileNotFoundError`

Run with:
```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
pytest tests/test_face.py -v
```
(The plugin-autoload flag works around an unrelated broken pytest plugin bundled inside `web3`.)

Search, validation, fingerprinting, and blockchain stages were verified through repeated live end-to-end runs during development (see console output patterns in the pipeline itself) rather than mocked unit tests, since their value lies specifically in live, non-deterministic, real-world behavior (live search results, real gas costs, real transaction hashes).

---

## Design Notes & Considerations

- **Search coverage reflects real-world indexing.** Reverse image search finds matches for images that are already publicly indexed online. Well-established profiles (LinkedIn, X, Pinterest) tend to surface reliably; some platforms like Instagram and Facebook restrict search-engine indexing of individual posts by design, so results there can be sparser. This is a property of the public web's indexing, not a gap in the pipeline itself — and it's precisely why Stage 3's independent validation matters, so an image with no genuine online presence correctly reports "no verified match" rather than a false positive.
- **Built-in safeguard against false positives.** Because visual-similarity ranking alone can occasionally surface a different, similar-looking person, FaceTrace adds its own independent face-embedding verification layer on top of the search results — so a "Verified Match" genuinely means the same face was confirmed, not just a visually similar photo.
- **The local blockchain is fully real, with one practical trade-off.** `eth-tester` provides a genuine EVM with real contracts and transactions, ideal for reliable local development and demonstration. Its state lives for the duration of one running process — a natural next step for production use would be pointing the same `web3.py` code at a persistent node or public testnet, which requires no changes to the verification logic itself, only the connection target.
- **SerpApi's free tier (100 searches/month)** comfortably covers development, testing, and demonstration use for a project at this scale.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'tf_keras'`**
Run `pip install tf-keras==2.16.0` — TensorFlow 2.16 defaults to Keras 3, but `deepface`'s detector backends expect the Keras 2 compatibility package.

**Blockchain step fails to reach `solc-bin.ethereum.org`**
See the Solidity compiler note in the Setup section above — some networks block this specific domain even when GitHub is reachable.

**`solcx.exceptions.SolcNotInstalled` even after placing the binary correctly**
`py-solc-x`'s automatic executable-path resolution has a known inconsistency on some Windows setups. `chain_client.py` works around this by pointing `solcx.compile_source()` directly at the manually-installed binary via the `solc_binary` parameter, bypassing the flaky lookup entirely.

**"No verified match found"**
This is expected, correct behavior when the input image isn't already indexed publicly online, or when the search only surfaces visually-similar-but-different people (which our validation step correctly rejects). Try a photo you know is already posted publicly (e.g., a LinkedIn profile photo), and confirm independently via a manual search on images.google.com before assuming there's a bug.

---

## What the Demo Shows

1. Full pipeline run: face scan → live search → verified match found → cryptographic fingerprint → blockchain upload
2. The discovered post's URL opened to confirm it's a real, existing page
3. `verify.py` run on the untouched evidence → **AUTHENTIC**
4. `verify.py` run on a deliberately edited copy of the same evidence → **TAMPERED**

---

## Contact

Ujwal U — ujwaljawalgi2208@gmail.com

Srilakshmi — dsrilakshmi@gmail.com

Team Pikachu, HH Goa 2026 (Task 3)
