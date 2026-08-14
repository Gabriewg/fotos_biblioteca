from pathlib import Path

from src.organizer import organize_photos

SAMPLE_PHOTOS = Path(__file__).resolve().parent.parent / "sample_photos"


def test_dry_run_nao_copia_arquivos(tmp_path):
    actions = organize_photos([SAMPLE_PHOTOS], tmp_path / "output", dry_run=True)

    ready = [a for a in actions if not a.skipped]
    assert len(ready) == 3
    assert all(a.destination.parent.name == "08-13" for a in ready)
    assert list((tmp_path / "output").rglob("*")) == []


def test_copia_organizada_por_data(tmp_path):
    output = tmp_path / "output"
    actions = organize_photos([SAMPLE_PHOTOS], output, dry_run=False)

    for action in actions:
        if action.skipped:
            continue
        assert action.destination.exists()
        assert action.destination.parent.name == "08-13"
        assert action.destination.parent.parent.name == "2026"


def test_arquivo_nao_foto_ignorado(tmp_path):
    actions = organize_photos([SAMPLE_PHOTOS / "not_an_image.txt"], tmp_path / "output")

    assert len(actions) == 1
    assert actions[0].skipped
    assert actions[0].skipped_reason == "não é foto"


def test_foto_sem_exif_organizada_por_data_de_modificacao(tmp_path):
    actions = organize_photos([SAMPLE_PHOTOS / "foto_sem_exif.jpg"], tmp_path / "output")

    assert len(actions) == 1
    assert not actions[0].skipped
    assert actions[0].destination.parent.name == "08-13"
    assert actions[0].destination.parent.parent.name == "2026"


def test_renomear_com_data_usa_nome_datado(tmp_path):
    actions = organize_photos(
        [SAMPLE_PHOTOS / "IMG_1422.JPG"], tmp_path / "output", rename_with_date=True
    )

    assert not actions[0].skipped
    assert actions[0].destination.name == "2026-08-13_19-14-02_IMG_1422.JPG"


def test_renomear_com_data_sem_duplicar_nome(tmp_path):
    photo = SAMPLE_PHOTOS / "IMG_1422.JPG"
    actions = organize_photos([photo, photo], tmp_path / "output", rename_with_date=True)

    ready = [a for a in actions if not a.skipped]
    assert len(ready) == 2
    names = {a.destination.name for a in ready}
    assert len(names) == 2
    assert "2026-08-13_19-14-02_IMG_1422.JPG" in names
