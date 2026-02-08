"""
Image processing utilities for Museum Guide MVP.
"""

import base64
import io
from typing import Tuple
from PIL import Image


def preprocess_image(
    image: Image.Image,
    max_size: Tuple[int, int] = (512, 512)
) -> Image.Image:
    """
    Preprocess image for API calls.

    Args:
        image: PIL Image object
        max_size: Maximum dimensions (width, height)

    Returns:
        Preprocessed PIL Image
    """
    # Convert to RGB if necessary
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Resize while maintaining aspect ratio
    image.thumbnail(max_size, Image.Resampling.LANCZOS)

    return image


def encode_image_base64(image: Image.Image, format: str = "JPEG") -> str:
    """
    Encode PIL Image to base64 string.

    Args:
        image: PIL Image object
        format: Image format (JPEG, PNG, etc.)

    Returns:
        Base64 encoded string
    """
    buffer = io.BytesIO()
    image.save(buffer, format=format, quality=85)
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def decode_image_base64(base64_string: str) -> Image.Image:
    """
    Decode base64 string to PIL Image.

    Args:
        base64_string: Base64 encoded image string

    Returns:
        PIL Image object
    """
    image_data = base64.b64decode(base64_string)
    return Image.open(io.BytesIO(image_data))


def bytes_to_image(image_bytes: bytes) -> Image.Image:
    """
    Convert bytes to PIL Image.

    Args:
        image_bytes: Image as bytes

    Returns:
        PIL Image object
    """
    return Image.open(io.BytesIO(image_bytes))


def image_to_bytes(image: Image.Image, format: str = "JPEG") -> bytes:
    """
    Convert PIL Image to bytes.

    Args:
        image: PIL Image object
        format: Image format

    Returns:
        Image as bytes
    """
    buffer = io.BytesIO()
    image.save(buffer, format=format, quality=85)
    buffer.seek(0)
    return buffer.getvalue()
