import io
import struct
from datetime import datetime
from pathlib import Path

from PIL import Image

from src.metadata import get_datetime_original, get_photo_datetime

SAMPLE_PHOTOS = Path(__file__).resolve().parent.parent / "sample_photos"


def _jpeg_with_exif(*, ifd0_has_datetime: bool) -> bytes:
    dt_sub = b"2024:05:10 12:30:00\x00"
    dt_ifd0 = b"2023:01:01 08:00:00\x00" if ifd0_has_datetime else None

    def entry(tag, etype, count, value):
        return struct.pack("<HHI", tag, etype, count) + struct.pack("<I", value)

    ifd0_count = 2 if dt_ifd0 else 1
    ifd0_size = 2 + 12 * ifd0_count + 4
    values_start = 8 + ifd0_size
    subifd_offset = values_start + (len(dt_ifd0) if dt_ifd0 else 0)
    if subifd_offset % 2:
        subifd_offset += 1

    ifd0 = bytearray(struct.pack("<H", ifd0_count))
    ifd0 += entry(0x8769, 4, 1, subifd_offset)
    if dt_ifd0:
        ifd0 += entry(306, 2, len(dt_ifd0), values_start)
    ifd0 += struct.pack("<I", 0)

    sub_size = 2 + 12 + 4
    dt_sub_offset = subifd_offset + sub_size
    sub = bytearray(struct.pack("<H", 1))
    sub += entry(36867, 2, len(dt_sub), dt_sub_offset)
    sub += struct.pack("<I", 0)

    tiff = b"II\x2a\x00" + struct.pack("<I", 8) + bytes(ifd0)
    if dt_ifd0:
        tiff += dt_ifd0
        if len(tiff) % 2:
            tiff += b"\x00"
    tiff += bytes(sub)
    tiff += dt_sub

    app1 = b"\xff\xe1" + struct.pack(">H", 8 + len(tiff)) + b"Exif\x00\x00" + tiff
    base = io.BytesIO()
    Image.new("RGB", (1, 1), "red").save(base, "JPEG")
    jpeg = base.getvalue()
    return jpeg[:2] + app1 + jpeg[2:]


def test_foto_com_exif_valido_retorna_datetime():
    photo = SAMPLE_PHOTOS / "IMG_1422.JPG"

    assert get_datetime_original(photo) == datetime(2026, 8, 13, 19, 14, 2)


def test_datetimeoriginal_na_subifd_e_priorizado(tmp_path):
    photo = tmp_path / "com_ambas.jpg"
    photo.write_bytes(_jpeg_with_exif(ifd0_has_datetime=True))

    assert get_datetime_original(photo) == datetime(2024, 5, 10, 12, 30, 0)


def test_datetimeoriginal_apenas_na_subifd(tmp_path):
    photo = tmp_path / "so_subifd.jpg"
    photo.write_bytes(_jpeg_with_exif(ifd0_has_datetime=False))

    assert get_datetime_original(photo) == datetime(2024, 5, 10, 12, 30, 0)


def test_foto_sem_exif_retorna_none():
    photo = SAMPLE_PHOTOS / "foto_sem_exif.jpg"

    assert get_datetime_original(photo) is None


def test_foto_sem_exif_fallback_usa_data_de_modificacao():
    photo = SAMPLE_PHOTOS / "foto_sem_exif.jpg"

    assert get_photo_datetime(photo) == datetime.fromtimestamp(photo.stat().st_mtime)


def test_arquivo_que_nao_e_imagem_retorna_none():
    not_an_image = SAMPLE_PHOTOS / "not_an_image.txt"

    assert get_datetime_original(not_an_image) is None


def test_caminho_inexistente_retorna_none():
    missing = SAMPLE_PHOTOS / "nao_existe.JPG"

    assert get_datetime_original(missing) is None
