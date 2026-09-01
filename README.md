# FaceTrace

FaceTrace is a Python-based application that integrates facial recognition (`deepface`, `tensorflow`), blockchain (`web3`), and search functionalities (`google-search-results`).

## Prerequisites

- Python 3.8+
- [Node.js / npm](https://nodejs.org/) (if running a local blockchain network like Hardhat or Ganache)

## Installation

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the environment variables:
   - Copy the `.env.example` file to `.env`:
     ```bash
     copy .env.example .env
     ```
   - Fill in your API keys and configuration in the `.env` file.

## Testing

To run the tests:
```bash
pytest
```
