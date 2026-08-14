import shutil
from dataclasses import dataclass
from pathlib import Path

from .metadata import get_photo_datetime

PHOTO_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".tiff", ".tif", ".webp", ".heic", ".heif",
    ".raw", ".cr2", ".nef", ".arw",
}


@dataclass
class PhotoAction:
    source: Path
    destination: Path | None = None
    skipped_reason: str | None = None

    @property
    def skipped(self) -> bool:
        return self.destination is None


def _expand_sources(sources: list[Path]) -> list[Path]:
    photos: list[Path] = []
    for source in sources:
        if source.is_dir():
            for photo in sorted(source.rglob("*")):
                if photo.is_file() and photo.suffix.lower() in PHOTO_EXTENSIONS:
                    photos.append(photo)
        elif source.is_file():
            photos.append(source)
    return photos


def plan_photos(sources: list[Path], output: Path, rename_with_date: bool = False) -> list[PhotoAction]:
    actions: list[PhotoAction] = []
    used_destinations: set[Path] = set()

    for photo in _expand_sources(sources):
        if photo.suffix.lower() not in PHOTO_EXTENSIONS:
            actions.append(PhotoAction(photo, skipped_reason="não é foto"))
            continue

        dt = get_photo_datetime(photo)
        if dt is None:
            actions.append(PhotoAction(photo, skipped_reason="sem data no EXIF"))
            continue

        folder = output / str(dt.year) / f"{dt.month:02d}-{dt.day:02d}"
        stem = f"{dt:%Y-%m-%d_%H-%M-%S}_{photo.stem}" if rename_with_date else photo.stem
        candidate = folder / f"{stem}{photo.suffix}"
        counter = 1
        while candidate in used_destinations or candidate.exists():
            candidate = folder / f"{stem}_{counter}{photo.suffix}"
            counter += 1
        used_destinations.add(candidate)
        actions.append(PhotoAction(photo, candidate))

    return actions


def organize_photos(
    sources: list[Path],
    output: Path,
    dry_run: bool = True,
    rename_with_date: bool = False,
) -> list[PhotoAction]:
    output = Path(output)
    actions = plan_photos(sources, output, rename_with_date=rename_with_date)
    results: list[PhotoAction] = []

    for action in actions:
        if action.skipped or dry_run:
            results.append(action)
            continue

        action.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(action.source, action.destination)
        results.append(action)

    return results
