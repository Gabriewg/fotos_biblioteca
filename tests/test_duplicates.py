from pathlib import Path

from src.duplicates import duplicate_groups, file_hash, group_duplicates


def test_group_duplicates_encontra_repetidas(tmp_path):
    a1 = tmp_path / "a1.jpg"
    a2 = tmp_path / "a2.jpg"
    b = tmp_path / "b.jpg"
    a1.write_bytes(b"mesmo-conteudo")
    a2.write_bytes(b"mesmo-conteudo")
    b.write_bytes(b"outro-conteudo")

    groups = group_duplicates([a1, a2, b])

    assert len(groups) == 1
    assert set(groups[0]) == {a1, a2}


def test_duplicate_groups_mantem_primeira(tmp_path):
    old = tmp_path / "a1.jpg"
    copy = tmp_path / "a2.jpg"
    old.write_bytes(b"xyz")
    copy.write_bytes(b"xyz")

    groups = duplicate_groups([copy, old])

    assert len(groups) == 1
    kept, dups = groups[0]
    assert kept.name == "a1.jpg"
    assert dups == [copy]


def test_file_hash_igual_para_mesmo_conteudo(tmp_path):
    f1 = tmp_path / "f1.jpg"
    f2 = tmp_path / "f2.jpg"
    f1.write_bytes(b"12345")
    f2.write_bytes(b"12345")

    assert file_hash(f1) == file_hash(f2)


def test_grupo_sem_duplicatas_retorna_vazio(tmp_path):
    f1 = tmp_path / "a.jpg"
    f2 = tmp_path / "b.jpg"
    f1.write_bytes(b"a")
    f2.write_bytes(b"b")

    assert group_duplicates([f1, f2]) == []


def test_arquivo_inexistente_e_ignorado(tmp_path):
    groups = group_duplicates([tmp_path / "sumiu.jpg"])

    assert groups == []