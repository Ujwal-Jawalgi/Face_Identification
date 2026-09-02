"""
FaceTrace - Tests for Phase 2: Face Detection & Encoding
"""

import os
import sys
import pytest

# Ensure src/ is importable when running pytest from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.face.detect_encode import detect_and_encode, FaceDetectionError

# Update these paths to match your actual test images
FACE_IMAGE_PATH = "data/input/test_face6.jpg"
NO_FACE_IMAGE_PATH = "data/input/mountain.jpg"


def test_detect_and_encode_returns_valid_embedding():
    """A real face image should produce a valid embedding + cropped face."""
    result = detect_and_encode(FACE_IMAGE_PATH)

    assert "embedding" in result
    assert isinstance(result["embedding"], list)
    assert len(result["embedding"]) == result["embedding_dim"]
    assert result["embedding_dim"] > 0

    assert os.path.exists(result["cropped_face_path"])
    assert result["source_image_path"] == FACE_IMAGE_PATH


def test_detect_and_encode_is_deterministic():
    """Running the same image twice should produce the same embedding."""
    result1 = detect_and_encode(FACE_IMAGE_PATH)
    result2 = detect_and_encode(FACE_IMAGE_PATH)

    assert result1["embedding"] == result2["embedding"]


def test_no_face_raises_face_detection_error():
    """An image with no face should raise FaceDetectionError, not crash."""
    with pytest.raises(FaceDetectionError):
        detect_and_encode(NO_FACE_IMAGE_PATH)


def test_missing_file_raises_file_not_found():
    """A nonexistent image path should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        detect_and_encode("data/input/this_file_does_not_exist.jpg")