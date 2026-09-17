import json

from scripts.treinar_multitarefa import ler_textos


def test_corpus_csv_remove_vazio_e_duplicado(tmp_path):
    caminho = tmp_path / "corpus.csv"
    caminho.write_text("texto,rotulo\nola,1\n,0\nola,1\ntchau,0\n", encoding="utf-8")

    assert ler_textos(caminho) == ["ola", "tchau"]


def test_corpus_jsonl_exige_campo_texto(tmp_path):
    caminho = tmp_path / "corpus.jsonl"
    caminho.write_text(
        "\n".join(json.dumps({"texto": texto}) for texto in ("um", "dois")),
        encoding="utf-8",
    )

    assert ler_textos(caminho) == ["um", "dois"]
