import csv
import hashlib
import json

from scripts.preparar_corpus_ironia import git_blob_sha1, limpar_texto, ler_arquivo


def test_checksum_e_o_formato_de_blob_do_git():
    dados = b"teste\n"
    esperado = hashlib.sha1(b"blob 6\0teste\n").hexdigest()
    assert git_blob_sha1(dados) == esperado


def test_remove_apenas_hashtag_que_vaza_o_rotulo():
    assert limpar_texto("Que ótimo #Ironia #atendimento") == "Que ótimo #atendimento"
    assert limpar_texto("#sarcasmo, claro") == "claro"


def test_le_json_aninhado_preservando_autor_quando_existe(tmp_path):
    caminho = tmp_path / "dados.json"
    caminho.write_text(json.dumps({"items": [{"title": "Notícia", "author": "Ana"}]}), encoding="utf-8")
    assert list(ler_arquivo(caminho, 1)) == [("Notícia", "Ana")]


def test_le_json_por_linha_usado_pelos_crawlers_publicos(tmp_path):
    caminho = tmp_path / "noticias.json"
    caminho.write_text(
        "\n".join(
            (
                json.dumps({"text": "Primeira", "author": "Ana"}),
                json.dumps({"text": "Segunda", "author": "Bia"}),
            )
        ),
        encoding="utf-8",
    )
    assert list(ler_arquivo(caminho, 1)) == [
        ("Primeira", "Ana"),
        ("Segunda", "Bia"),
    ]


def test_csv_sem_cabecalho_escolhe_a_coluna_textual(tmp_path):
    caminho = tmp_path / "tweets.csv"
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        csv.writer(arquivo).writerow(["123", "texto bem maior"])
    assert list(ler_arquivo(caminho, 1)) == [("texto bem maior", None)]
