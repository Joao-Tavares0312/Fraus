import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from fraus.api.esquemas import PedidoSimulacao
from fraus.api.rotas import modelo
from fraus.comparacao_modelos import avaliar_conjunto, montar_laudo
from fraus.sinais.emocao import NOMES_EMOCOES


def _laudo():
    rotulos = [0, 1] * 10
    conjunto = avaliar_conjunto(
        identificador="ironia_interno", tarefa="ironia", nome="Ironia — teste interno",
        independente=False, rotulos=rotulos,
        preditos_por_modelo={"bertimbau": [0] * 20, "laya_treinado": list(rotulos)},
        classes=[0, 1], nomes_classes=["nao-ironico", "ironico"], reamostras=100,
    )
    return montar_laudo(conjuntos=[conjunto], latencia=None, procedencia={},
                        rodada_de_fumaca=False, gerado_em="2026-10-02T13:00:00+00:00")


def test_sem_laudo_a_rota_diz_que_nao_ha_e_nao_inventa(tmp_path, monkeypatch):
    monkeypatch.setattr(modelo, "CAMINHO_COMPARACAO", tmp_path / "comparacao_modelos.json")
    monkeypatch.setattr(modelo, "CAMINHO_COMPARACAO_PUBLICADA", tmp_path / "publicado.json",
                        raising=False)
    assert modelo.comparacao() == {"laudo": None}


def test_laudo_gravado_e_servido_como_esta(tmp_path, monkeypatch):
    caminho = tmp_path / "comparacao_modelos.json"
    caminho.write_text(json.dumps(_laudo()), encoding="utf-8")
    monkeypatch.setattr(modelo, "CAMINHO_COMPARACAO", caminho)
    assert modelo.comparacao()["laudo"] == _laudo()


@pytest.mark.parametrize("conteudo", ["{nao e json", json.dumps({"schema": 9, "conjuntos": []})])
def test_laudo_ilegivel_e_erro_alto_e_nao_tela_vazia(tmp_path, monkeypatch, conteudo):
    caminho = tmp_path / "comparacao_modelos.json"
    caminho.write_text(conteudo, encoding="utf-8")
    monkeypatch.setattr(modelo, "CAMINHO_COMPARACAO", caminho)
    with pytest.raises(HTTPException) as erro:
        modelo.comparacao()
    assert erro.value.status_code == 500


def test_relatorio_sai_em_markdown_para_baixar(tmp_path, monkeypatch):
    caminho = tmp_path / "comparacao_modelos.json"
    caminho.write_text(json.dumps(_laudo()), encoding="utf-8")
    monkeypatch.setattr(modelo, "CAMINHO_COMPARACAO", caminho)
    resposta = modelo.relatorio_comparacao()
    assert resposta.media_type.startswith("text/markdown")
    assert "attachment" in resposta.headers["content-disposition"]
    assert "Ironia — teste interno" in resposta.body.decode("utf-8")


def test_relatorio_sem_laudo_e_404(tmp_path, monkeypatch):
    monkeypatch.setattr(modelo, "CAMINHO_COMPARACAO", tmp_path / "nao-existe.json")
    monkeypatch.setattr(modelo, "CAMINHO_COMPARACAO_PUBLICADA", tmp_path / "publicado.json",
                        raising=False)
    with pytest.raises(HTTPException) as erro:
        modelo.relatorio_comparacao()
    assert erro.value.status_code == 404


class MotorFalso:
    def ler_cabecas(self, texto):
        emocao = [0.0] * len(NOMES_EMOCOES)
        emocao[NOMES_EMOCOES.index("raiva")] = 1.0
        return {
            "emocao": {"probabilidades": emocao, "ms": 12.0},
            "ironia": {"prob_ironia": 0.8, "ms": 9.0},
            "passada_unica": False,
        }


def _ctx():
    return SimpleNamespace(motor=MotorFalso())


def test_frase_ao_vivo_com_backend_padrao_mostra_bertimbau_e_nomeia_o_laya_ausente(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("FRAUS_IRONIA_BACKEND", raising=False)
    monkeypatch.setattr(modelo, "CAMINHO_ONNX_LAYA", tmp_path / "laya-ironia")
    resposta = modelo.simular_comparacao(PedidoSimulacao(texto=" que absurdo "), _ctx())

    ironia = resposta["tarefas"]["ironia"]
    assert ironia["bertimbau"] == {
        "disponivel": True, "prob_ironia": 0.8, "classe": "ironico", "ms": 9.0,
        "executor": "torch",
    }
    assert ironia["laya"]["disponivel"] is False
    assert "laya.onnx" in ironia["laya"]["motivo"]
    emocao = resposta["tarefas"]["emocao"]
    assert emocao["bertimbau"]["classe"] == "raiva"
    assert emocao["bertimbau"]["probabilidades"]["raiva"] == 1.0
    assert emocao["laya"]["disponivel"] is False
    assert resposta["texto"] == "que absurdo"
    assert resposta["pontua"] is False


def test_com_backend_laya_a_cabeca_em_uso_e_o_laya_e_o_bertimbau_de_ironia_falta(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("FRAUS_IRONIA_BACKEND", "laya-onnx")
    monkeypatch.setattr(modelo, "CAMINHO_ONNX_LAYA", tmp_path / "laya-ironia")
    ironia = modelo.simular_comparacao(PedidoSimulacao(texto="otimo"), _ctx())["tarefas"]["ironia"]
    assert ironia["laya"]["disponivel"] is True
    assert ironia["laya"]["executor"] == "laya-onnx"
    assert ironia["laya"]["prob_ironia"] == 0.8
    assert ironia["bertimbau"]["disponivel"] is False
    assert "FRAUS_IRONIA_BACKEND" in ironia["bertimbau"]["motivo"]


def test_laya_treinado_no_servidor_responde_ironia_e_emocao(tmp_path, monkeypatch):
    pasta = tmp_path / "laya-ironia"
    pasta.mkdir()
    (pasta / "laya.onnx").write_bytes(b"x")
    (pasta / "manifesto.json").write_text(json.dumps({"perguntas": ["emocao", "ironia"]}))
    monkeypatch.delenv("FRAUS_IRONIA_BACKEND", raising=False)
    monkeypatch.setattr(modelo, "CAMINHO_ONNX_LAYA", pasta)

    class IroniaFalsa:
        def prever_mensagens(self, textos):
            return [[0.7, 0.3]]

    class EmocaoFalsa:
        def prever_mensagens(self, textos):
            p = [0.0] * len(NOMES_EMOCOES)
            p[NOMES_EMOCOES.index("nojo")] = 1.0
            return [p]

    import fraus.sinais.emocao_laya as emocao_laya
    import fraus.sinais.ironia_laya as ironia_laya

    monkeypatch.setattr(ironia_laya, "obter_classificador_ironia_laya_onnx", lambda: IroniaFalsa())
    monkeypatch.setattr(emocao_laya, "obter_classificador_emocao_laya_onnx", lambda: EmocaoFalsa())

    tarefas = modelo.simular_comparacao(PedidoSimulacao(texto="eca"), _ctx())["tarefas"]
    assert tarefas["ironia"]["laya"]["classe"] == "nao-ironico"
    assert tarefas["ironia"]["laya"]["prob_ironia"] == 0.3
    assert tarefas["ironia"]["laya"]["ms"] >= 0
    assert tarefas["emocao"]["laya"]["classe"] == "nojo"
    assert tarefas["emocao"]["laya"]["treinado"] is True
    assert tarefas["ironia"]["laya"]["treinado"] is True


def test_laya_sem_treino_le_emocao_e_a_leitura_sai_marcada_como_sem_treino(
    tmp_path, monkeypatch
):
    pasta = tmp_path / "laya-ironia"
    pasta.mkdir()
    (pasta / "laya.onnx").write_bytes(b"x")
    (pasta / "manifesto.json").write_text(json.dumps({"formato": "int8"}))  # notebook 06
    monkeypatch.delenv("FRAUS_IRONIA_BACKEND", raising=False)
    monkeypatch.setattr(modelo, "CAMINHO_ONNX_LAYA", pasta)

    import fraus.sinais.emocao_laya as emocao_laya
    import fraus.sinais.ironia_laya as ironia_laya

    class IroniaFalsa:
        def prever_mensagens(self, textos):
            return [[0.4, 0.6]]

    class EmocaoFalsa:
        def prever_mensagens(self, textos):
            p = [0.0] * len(NOMES_EMOCOES)
            p[NOMES_EMOCOES.index("tristeza")] = 1.0
            return [p]

    monkeypatch.setattr(ironia_laya, "obter_classificador_ironia_laya_onnx", lambda: IroniaFalsa())
    monkeypatch.setattr(emocao_laya, "obter_classificador_emocao_laya_onnx", lambda: EmocaoFalsa())
    tarefas = modelo.simular_comparacao(PedidoSimulacao(texto="oi"), _ctx())["tarefas"]
    assert tarefas["emocao"]["laya"]["disponivel"] is True
    assert tarefas["emocao"]["laya"]["classe"] == "tristeza"
    assert tarefas["emocao"]["laya"]["treinado"] is False
    assert tarefas["ironia"]["laya"]["treinado"] is False
    assert "treinado" not in tarefas["emocao"]["bertimbau"]


def test_com_backend_laya_a_emocao_do_laya_tambem_sai_marcada(tmp_path, monkeypatch):
    pasta = tmp_path / "laya-ironia"
    pasta.mkdir()
    (pasta / "laya.onnx").write_bytes(b"x")
    monkeypatch.setenv("FRAUS_IRONIA_BACKEND", "laya-onnx")
    monkeypatch.setattr(modelo, "CAMINHO_ONNX_LAYA", pasta)

    import fraus.sinais.emocao_laya as emocao_laya

    class EmocaoFalsa:
        def prever_mensagens(self, textos):
            return [[1.0] + [0.0] * (len(NOMES_EMOCOES) - 1)]

    monkeypatch.setattr(emocao_laya, "obter_classificador_emocao_laya_onnx", lambda: EmocaoFalsa())
    tarefas = modelo.simular_comparacao(PedidoSimulacao(texto="oi"), _ctx())["tarefas"]
    assert tarefas["ironia"]["laya"]["treinado"] is False
    assert tarefas["emocao"]["laya"] == {**tarefas["emocao"]["laya"], "treinado": False,
                                         "classe": "alegria", "executor": "laya-onnx"}


def test_frase_ao_vivo_recusa_texto_vazio_e_motor_sem_cabecas():
    with pytest.raises(HTTPException, match="texto vazio"):
        modelo.simular_comparacao(PedidoSimulacao(texto="  "), _ctx())
    with pytest.raises(HTTPException) as erro:
        modelo.simular_comparacao(PedidoSimulacao(texto="oi"), SimpleNamespace(motor=object()))
    assert erro.value.status_code == 409


# --- laudo publicado com o codigo ---------------------------------------------

def test_sem_laudo_local_a_rota_serve_o_publicado_com_o_codigo(tmp_path, monkeypatch):
    publicado = tmp_path / "publicado.json"
    publicado.write_text(json.dumps(_laudo()), encoding="utf-8")
    monkeypatch.setattr(modelo, "CAMINHO_COMPARACAO", tmp_path / "nao-existe.json")
    monkeypatch.setattr(modelo, "CAMINHO_COMPARACAO_PUBLICADA", publicado)
    assert modelo.comparacao()["laudo"] == _laudo()


def test_laudo_local_vence_o_publicado(tmp_path, monkeypatch):
    local, publicado = tmp_path / "local.json", tmp_path / "publicado.json"
    local.write_text(json.dumps({**_laudo(), "gerado_em": "2026-10-03T00:00:00+00:00"}),
                     encoding="utf-8")
    publicado.write_text(json.dumps(_laudo()), encoding="utf-8")
    monkeypatch.setattr(modelo, "CAMINHO_COMPARACAO", local)
    monkeypatch.setattr(modelo, "CAMINHO_COMPARACAO_PUBLICADA", publicado)
    assert modelo.comparacao()["laudo"]["gerado_em"] == "2026-10-03T00:00:00+00:00"


def test_o_laudo_publicado_no_repositorio_e_valido():
    from fraus.api.caminhos import CAMINHO_COMPARACAO_PUBLICADA
    from fraus.comparacao_modelos import relatorio_markdown, validar_laudo

    laudo = json.loads(CAMINHO_COMPARACAO_PUBLICADA.read_text(encoding="utf-8"))
    validar_laudo(laudo)
    assert laudo["rodada_de_fumaca"] is False
    assert relatorio_markdown(laudo)
