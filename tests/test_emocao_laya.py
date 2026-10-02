import json

import pytest

from fraus.sinais.emocao import NOMES_EMOCOES
from fraus.sinais.emocao_laya import (
    ClassificadorEmocaoLayaOnnx,
    laya_treinado_pelo_fraus,
    perguntas_do_artefato,
)
from fraus.treino_laya import PERGUNTA_EMOCAO


class AgenteFalso:
    def __init__(self):
        self.chamadas = []

    def predict_batch(self, estados, perguntas, **opcoes):
        self.chamadas.append((estados, perguntas, opcoes))
        return [{"answers": {"emocao": {"probabilities": {
            nome: (0.4 if nome == "medo" else 0.1) for nome in NOMES_EMOCOES
        }}}}]


def test_emocao_pelo_laya_usa_a_pergunta_do_treino_uma_frase_por_chamada():
    agente = AgenteFalso()
    saida = ClassificadorEmocaoLayaOnnx(agente).prever_mensagens(["tenho medo", "de novo"])
    assert len(saida) == 2 and len(saida[0]) == len(NOMES_EMOCOES)
    assert saida[0][NOMES_EMOCOES.index("medo")] == 0.4
    assert [c[0] for c in agente.chamadas] == [["tenho medo"], ["de novo"]]
    assert all(c[1] == PERGUNTA_EMOCAO for c in agente.chamadas)


def test_manifesto_declara_as_perguntas_e_artefato_antigo_so_tem_ironia(tmp_path):
    assert perguntas_do_artefato(tmp_path) == ("ironia",)
    (tmp_path / "manifesto.json").write_text(json.dumps({"formato": "int8"}))
    assert perguntas_do_artefato(tmp_path) == ("ironia",)
    (tmp_path / "manifesto.json").write_text(json.dumps({"perguntas": ["emocao", "ironia"]}))
    assert perguntas_do_artefato(tmp_path) == ("emocao", "ironia")


def test_so_o_artefato_do_notebook_07_conta_como_treinado(tmp_path):
    assert laya_treinado_pelo_fraus(tmp_path) is False
    (tmp_path / "manifesto.json").write_text(json.dumps({"formato": "fp32"}))  # notebook 06
    assert laya_treinado_pelo_fraus(tmp_path) is False
    (tmp_path / "manifesto.json").write_text(json.dumps({"perguntas": ["emocao", "ironia"]}))
    assert laya_treinado_pelo_fraus(tmp_path) is True


def test_checkpoint_sem_treino_tambem_le_emocao_pelo_mesmo_agente(monkeypatch):
    # Em producao o Laya carregado e o checkpoint base. Ele responde a pergunta
    # de emocao a frio; quem diz que e "sem treino" e a rota, nao uma recusa.
    import fraus.sinais.emocao_laya as modulo
    import fraus.sinais.ironia_laya as ironia_laya

    agente = AgenteFalso()
    monkeypatch.setattr(ironia_laya, "obter_classificador_ironia_laya_onnx",
                        lambda: type("Ironia", (), {"_agente": agente})())
    modulo.obter_classificador_emocao_laya_onnx.cache_clear()
    saida = modulo.obter_classificador_emocao_laya_onnx().prever_mensagens(["socorro"])
    modulo.obter_classificador_emocao_laya_onnx.cache_clear()
    assert saida[0][NOMES_EMOCOES.index("medo")] == 0.4
