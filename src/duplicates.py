import hashlib
from pathlib import Path

_CHUNK_SIZE = 1 << 20


def file_hash(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(_CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def group_duplicates(photos: list[Path]) -> list[list[Path]]:
    by_hash: dict[str, list[Path]] = {}
    for photo in photos:
        try:
            digest = file_hash(photo)
        except OSError:
            continue
        by_hash.setdefault(digest, []).append(photo)
    return [group for group in by_hash.values() if len(group) > 1]


def duplicate_groups(photos: list[Path]) -> list[tuple[Path, list[Path]]]:
    groups = group_duplicates(photos)
    result = []
    for group in groups:
        group = sorted(group, key=lambda p: str(p))
        result.append((group[0], group[1:]))
    return result