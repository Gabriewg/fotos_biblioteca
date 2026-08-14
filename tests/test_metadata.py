from datetime import datetime
from pathlib import Path

from src.metadata import get_datetime_original, get_photo_datetime

SAMPLE_PHOTOS = Path(__file__).resolve().parent.parent / "sample_photos"


def test_foto_com_exif_valido_retorna_datetime():
    photo = SAMPLE_PHOTOS / "IMG_1422.JPG"

    assert get_datetime_original(photo) == datetime(2026, 8, 13, 19, 14, 2)


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
