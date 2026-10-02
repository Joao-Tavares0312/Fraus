import json

import pytest

from fraus.sinais.emocao import NOMES_EMOCOES
from fraus.sinais.emocao_laya import (
    ClassificadorEmocaoLayaOnnx,
    EmocaoLayaIndisponivelError,
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


def test_obter_emocao_recusa_artefato_sem_treino_de_emocao(tmp_path, monkeypatch):
    import fraus.sinais.emocao_laya as modulo

    monkeypatch.setattr(modulo, "_diretorio_do_artefato", lambda: tmp_path)
    modulo.obter_classificador_emocao_laya_onnx.cache_clear()
    with pytest.raises(EmocaoLayaIndisponivelError):
        modulo.obter_classificador_emocao_laya_onnx()
