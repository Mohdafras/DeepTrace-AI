"""Validate in-memory image bytes; multipart uploads may spool to temporary disk."""
from io import BytesIO
from pathlib import PurePosixPath
import warnings

from PIL import Image, UnidentifiedImageError

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGE_PIXELS = 20_000_000


def safe_filename(filename: str) -> str:
    """Store a basename, never an uploaded path or control characters."""
    name = PurePosixPath(filename.replace("\\", "/")).name
    return "".join(char for char in name if char.isprintable())[:255]


def decode_image(content: bytes, filename: str) -> Image.Image:
    """Verify extension, actual codec and decoded size before allocating RGB."""
    if PurePosixPath(filename.lower()).suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file format. Use JPG, JPEG, PNG, or WEBP.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                if source.format not in ALLOWED_FORMATS:
                    raise ValueError("Unsupported image content. Use JPEG, PNG, or WEBP.")
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise ValueError("Image exceeds the 20 megapixel decoded-image limit.")
                if getattr(source, "is_animated", False):
                    raise ValueError("Animated images are not supported. Upload a still image.")
                source.verify()
            with Image.open(BytesIO(content)) as source:
                return source.convert("RGB")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("Image dimensions are too large to process safely.") from exc
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValueError("The uploaded file is not a valid, readable image.") from exc
