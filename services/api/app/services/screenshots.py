import io
import re
import warnings
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings

MAX_BYTES = 5_000_000
MAX_PIXELS = 16_000_000


def storage_path(name):
    if not re.fullmatch(r"[a-f0-9]{32}\.png", name):
        raise HTTPException(404, "Screenshot not found.")
    root = Path(get_settings().upload_dir).resolve()
    target = (root / name).resolve()
    if target.parent != root:
        raise HTTPException(404, "Screenshot not found.")
    return target


def save_image(payload):
    if len(payload) > MAX_BYTES:
        raise HTTPException(413, "Screenshot must be smaller than 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(payload)) as image:
                if image.format not in ("PNG", "JPEG", "WEBP"):
                    raise ValueError("Use PNG, JPEG or WebP.")
                if image.width * image.height > MAX_PIXELS:
                    raise ValueError("Screenshot is too large (maximum 16 million pixels).")
                image.load()
                # Re-encode pixel data: remove EXIF, filenames and embedded metadata.
                clean = Image.new("RGB", image.size)
                clean.paste(image.convert("RGB"))
                name = f"{uuid4().hex}.png"
                path = storage_path(name)
                path.parent.mkdir(parents=True, exist_ok=True)
                clean.save(path, format="PNG")
                return name
    except (
        UnidentifiedImageError,
        ValueError,
        OSError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as exc:
        raise HTTPException(
            422, "Invalid image. Use PNG, JPEG or WebP within size limits."
        ) from exc


def remove_image(name):
    if name:
        storage_path(name).unlink(missing_ok=True)
