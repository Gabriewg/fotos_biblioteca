from datetime import datetime
from pathlib import Path

import pillow_heif
from PIL import ExifTags, Image

pillow_heif.register_heif_opener()

EXIF_DATETIME_ORIGINAL = 36867
EXIF_DATETIME = 306


def _parse_exif_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def get_datetime_original(path: Path) -> datetime | None:
    try:
        image = Image.open(path)
        try:
            exif = image.getexif()
            exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
        finally:
            image.close()
    except Exception:
        return None

    return (
        _parse_exif_datetime(exif_ifd.get(EXIF_DATETIME_ORIGINAL))
        or _parse_exif_datetime(exif_ifd.get(EXIF_DATETIME))
        or _parse_exif_datetime(exif.get(EXIF_DATETIME))
    )


def get_photo_datetime(path: Path) -> datetime | None:
    dt = get_datetime_original(path)
    if dt is not None:
        return dt
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return None
