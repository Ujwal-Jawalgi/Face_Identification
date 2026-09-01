"""
FaceTrace - Phase 2: Face Detection & Encoding
Detects a face in an input image, saves a cropped version,
and generates an embedding vector representing that face.
"""

import os
import json
from deepface import DeepFace


class FaceDetectionError(Exception):
    """Raised when no face can be detected in the input image."""
    pass


def detect_and_encode(image_path: str, output_dir: str = "data/evidence") -> dict:
    """
    Detects a face in the given image, saves the cropped face,
    and generates an embedding vector.

    Args:
        image_path: path to the input image file.
        output_dir: where to save the cropped face + metadata.

    Returns:
        dict with keys:
            - embedding: list[float]  (the face encoding vector)
            - embedding_model: str
            - cropped_face_path: str (path to saved cropped face image)
            - source_image_path: str

    Raises:
        FaceDetectionError: if no face is detected.
        FileNotFoundError: if image_path does not exist.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image not found: {image_path}")

    os.makedirs(output_dir, exist_ok=True)

    model_name = "Facenet"  # good balance of speed/accuracy, well-supported by deepface

    try:
        # DeepFace.represent handles detection + encoding in one call.
        # enforce_detection=True means it will raise if no face is found,
        # instead of silently returning garbage.
        results = DeepFace.represent(
            img_path=image_path,
            model_name=model_name,
            enforce_detection=True,
            detector_backend="opencv",
        )
    except ValueError as e:
        # DeepFace raises ValueError internally when it can't find a face
        raise FaceDetectionError(
            f"No face detected in '{image_path}'. Try a clearer, front-facing photo. "
            f"Original error: {e}"
        )

    if not results:
        raise FaceDetectionError(f"No face detected in '{image_path}'.")

    # If multiple faces are found, take the first (largest/most confident) one
    face_data = results[0]
    embedding = face_data["embedding"]
    facial_area = face_data["facial_area"]

    # Save a cropped version of the detected face for evidence/demo purposes
    cropped_face_path = _save_cropped_face(image_path, facial_area, output_dir)

    return {
        "embedding": embedding,
        "embedding_model": model_name,
        "embedding_dim": len(embedding),
        "cropped_face_path": cropped_face_path,
        "source_image_path": image_path,
        "facial_area": facial_area,
    }


def _save_cropped_face(image_path: str, facial_area: dict, output_dir: str) -> str:
    """Crops the detected face region from the source image and saves it."""
    from PIL import Image

    img = Image.open(image_path)
    x, y, w, h = (
        facial_area["x"],
        facial_area["y"],
        facial_area["w"],
        facial_area["h"],
    )
    cropped = img.crop((x, y, x + w, y + h))

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    cropped_path = os.path.join(output_dir, f"{base_name}_cropped_face.jpg")
    cropped.convert("RGB").save(cropped_path, "JPEG")

    return cropped_path


if __name__ == "__main__":
    # Manual quick-test entrypoint: python src/face/detect_encode.py <image_path>
    import sys

    if len(sys.argv) < 2:
        print("Usage: python src/face/detect_encode.py <path_to_image>")
        sys.exit(1)

    result = detect_and_encode(sys.argv[1])
    print(f"Face detected. Model: {result['embedding_model']}")
    print(f"Embedding dimension: {result['embedding_dim']}")
    print(f"Cropped face saved to: {result['cropped_face_path']}")
    print(f"Facial area: {result['facial_area']}")