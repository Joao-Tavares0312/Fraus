"""Os dois scripts do dev: criar links de anotador e exportar as respostas.

Sem rede: a chamada HTTP e injetada. O que importa conferir e a URL, a
credencial no cabecalho (e nunca na saida) e o link no formato da dashboard.
"""

import io
import json

from scripts import criar_link_anotacao, exportar_anotacao

CHAVE = "fra_chave-que-nao-pode-vazar"


class Resposta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def gravador(corpo):
    pedidos = []

    def abrir(pedido, timeout):
        pedidos.append(pedido)
        return Resposta(json.dumps(corpo).encode())

    return pedidos, abrir


def test_criar_links_chama_a_api_e_monta_o_link_da_dashboard():
    pedidos, abrir = gravador({"anotador": "a_0000beef", "token": "tok-123"})
    links = criar_link_anotacao.criar_links(
        "https://api.exemplo/", CHAVE, "https://painel.exemplo", 2, abrir=abrir,
    )
    assert links == [("a_0000beef", "https://painel.exemplo/anotar/tok-123")] * 2
    assert [p.full_url for p in pedidos] == ["https://api.exemplo/anotacao/anotadores"] * 2
    assert all(p.get_method() == "POST" for p in pedidos)
    assert pedidos[0].get_header("Authorization") == f"Bearer {CHAVE}"


def test_criar_link_nao_imprime_a_chave(monkeypatch, capsys):
    _, abrir = gravador({"anotador": "a_0000beef", "token": "tok-123"})
    monkeypatch.setenv("FRAUS_CHAVE_ACESSO", CHAVE)
    monkeypatch.setattr(criar_link_anotacao, "abrir_url", abrir)
    criar_link_anotacao.main(["--quantos", "1"])
    saida = capsys.readouterr()
    assert "https://fraus.vercel.app/anotar/tok-123" in saida.out
    assert CHAVE not in saida.out + saida.err


def test_exportar_grava_a_lista_de_registros(tmp_path, monkeypatch):
    registros = [{"anotador": "a_1", "frase_id": "f", "resposta": "ironico", "instante": "x"}]
    pedidos, abrir = gravador(registros)
    monkeypatch.setenv("FRAUS_CHAVE_ACESSO", CHAVE)
    monkeypatch.setattr(exportar_anotacao, "abrir_url", abrir)
    destino = tmp_path / "respostas.json"
    exportar_anotacao.main([str(destino)])
    assert json.loads(destino.read_text(encoding="utf-8")) == registros
    assert pedidos[0].full_url == "https://fraus-api.vercel.app/anotacao/respostas"
    assert pedidos[0].get_method() == "GET"
