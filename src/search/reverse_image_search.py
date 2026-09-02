"""
FaceTrace - Phase 3: Genuine Reverse Image Search via SerpApi (Google Lens)
Uploads an image to SerpApi and performs a real, live, dynamic search.
No hardcoded or pre-selected results - every call hits SerpApi live.
"""

import os
import io
import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

SERPAPI_UPLOAD_URL = "https://serpapi.com/image"
SERPAPI_SEARCH_URL = "https://serpapi.com/search"
MAX_UPLOAD_BYTES = 500 * 1024  # SerpApi's hard limit: 500 KB


class SerpApiError(Exception):
    """Raised when SerpApi upload or search fails."""
    pass


def _get_api_key() -> str:
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key or api_key == "your_serpapi_key_here":
        raise SerpApiError(
            "SERPAPI_API_KEY is not set in .env. Get a free key at serpapi.com."
        )
    return api_key


def _prepare_image_under_limit(image_path: str) -> bytes:
    """
    Ensures the image is under SerpApi's 500KB limit and in an accepted format
    (JPEG/PNG/WebP). Compresses/resizes progressively if needed.
    Returns raw image bytes ready for upload.
    """
    img = Image.open(image_path).convert("RGB")

    quality = 90
    max_dimension = 1600

    while True:
        # Resize if needed
        if max(img.size) > max_dimension:
            img.thumbnail((max_dimension, max_dimension))

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        size = buffer.tell()

        if size <= MAX_UPLOAD_BYTES:
            return buffer.getvalue()

        # Reduce quality/dimension progressively and retry
        if quality > 40:
            quality -= 10
        elif max_dimension > 600:
            max_dimension = int(max_dimension * 0.8)
        else:
            # Last resort - return whatever we have, even if slightly over
            return buffer.getvalue()


def upload_image_to_serpapi(image_path: str) -> str:
    """
    Uploads an image to SerpApi's Image API and returns a temporary image_id.
    The image_id expires after 10 minutes.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    api_key = _get_api_key()
    image_bytes = _prepare_image_under_limit(image_path)

    files = {"image": ("upload.jpg", image_bytes, "image/jpeg")}
    data = {"api_key": api_key}

    response = requests.post(SERPAPI_UPLOAD_URL, files=files, data=data, timeout=30)

    if response.status_code != 200:
        raise SerpApiError(
            f"SerpApi image upload failed (status {response.status_code}): {response.text}"
        )

    result = response.json()
    image_id = result.get("image_id")

    if not image_id:
        raise SerpApiError(f"SerpApi upload response missing image_id: {result}")

    return image_id


def search_by_image(image_path: str) -> dict:
    """
    Performs a genuine, live reverse image search using Google Lens via SerpApi.

    Returns the raw JSON response from SerpApi, which includes (among other things)
    a 'visual_matches' list of real candidate pages/posts found live at request time.

    Raises:
        SerpApiError: on upload or search failure.
        FileNotFoundError: if image_path doesn't exist.
    """
    api_key = _get_api_key()
    image_id = upload_image_to_serpapi(image_path)

    params = {
        "engine": "google_lens",
        "image_id": image_id,
        "api_key": api_key,
    }

    response = requests.get(SERPAPI_SEARCH_URL, params=params, timeout=60)

    if response.status_code != 200:
        raise SerpApiError(
            f"SerpApi search failed (status {response.status_code}): {response.text}"
        )

    result = response.json()

    if "error" in result:
        raise SerpApiError(f"SerpApi returned an error: {result['error']}")

    return result


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python src/search/reverse_image_search.py <path_to_image>")
        sys.exit(1)

    print("Uploading image and performing live SerpApi/Google Lens search...")
    results = search_by_image(sys.argv[1])

    visual_matches = results.get("visual_matches", [])
    print(f"\nFound {len(visual_matches)} visual match(es).\n")

    for i, match in enumerate(visual_matches[:10], start=1):
        print(f"--- Match {i} ---")
        print(f"Title:  {match.get('title')}")
        print(f"Link:   {match.get('link')}")
        print(f"Source: {match.get('source')}")
        print()

    # Save full raw response for inspection/debugging
    os.makedirs("data/evidence", exist_ok=True)
    with open("data/evidence/last_search_raw.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("Full raw response saved to data/evidence/last_search_raw.json")