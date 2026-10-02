import json

import pytest

from fraus.sinais.emocao import NOMES_EMOCOES
from fraus.sinais.ironia_laya import PERGUNTA_IRONIA
from fraus.treino_laya import (
    PERGUNTA_EMOCAO,
    caso_emocao,
    caso_ironia,
    distribuicao_de_rotulo,
    distribuicao_de_votos,
    mapa_de_poda,
    probabilidades_emocao,
    repeticoes_por_classe,
)


def test_pergunta_de_emocao_segue_a_ordem_do_pacote():
    # A ordem das opcoes e a ordem em que as probabilidades sao lidas depois.
    assert list(PERGUNTA_EMOCAO["emocao"]["criteria"]) == NOMES_EMOCOES
    assert PERGUNTA_EMOCAO["emocao"]["type"] == "choice"


def test_votos_viram_distribuicao():
    assert distribuicao_de_votos([3, 1, 0]) == [0.75, 0.25, 0.0]


def test_votos_zerados_levantam_em_vez_de_virar_uniforme():
    # O script do Laya troca soma zero por distribuicao uniforme em silencio:
    # um exemplo sem rotulo treinaria o modelo a nao saber.
    with pytest.raises(ValueError):
        distribuicao_de_votos([0, 0, 0])
    with pytest.raises(ValueError):
        distribuicao_de_votos([2, -1])


def test_rotulo_duro_e_suavizado():
    assert distribuicao_de_rotulo(1, 3) == [0.0, 1.0, 0.0]
    suave = distribuicao_de_rotulo(0, 4, suavizacao=0.1)
    assert suave == pytest.approx([0.925, 0.025, 0.025, 0.025])
    assert sum(suave) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        distribuicao_de_rotulo(3, 3)


def test_caso_de_emocao_tem_o_esquema_do_laya():
    distribuicao = [0.0] * len(NOMES_EMOCOES)
    distribuicao[NOMES_EMOCOES.index("raiva")] = 0.75
    distribuicao[NOMES_EMOCOES.index("nojo")] = 0.25
    caso = caso_emocao("que absurdo", distribuicao)
    assert caso["state"] == "que absurdo"
    assert caso["questions"] == PERGUNTA_EMOCAO
    probabilidades = caso["gold"]["emocao"]["probabilities"]
    assert list(probabilidades) == NOMES_EMOCOES
    assert probabilidades["raiva"] == 0.75 and probabilidades["nojo"] == 0.25
    json.dumps(caso)  # uma linha do JSONL


def test_caso_de_emocao_recusa_distribuicao_do_tamanho_errado():
    with pytest.raises(ValueError):
        caso_emocao("oi", [1.0, 0.0])
    with pytest.raises(ValueError):
        caso_emocao("  ", [1.0] + [0.0] * (len(NOMES_EMOCOES) - 1))


def test_caso_de_ironia_usa_a_mesma_pergunta_da_inferencia():
    # Treinar numa pergunta e servir outra e treinar o modelo errado.
    caso = caso_ironia("otimo, so esperei 3 horas", 1.0)
    assert caso["questions"] == PERGUNTA_IRONIA
    assert caso["gold"]["ironia"]["probabilities"] == {"A": 1.0, "B": 0.0}
    with pytest.raises(ValueError):
        caso_ironia("oi", 1.2)


def test_repeticoes_compensam_a_classe_rara_com_teto():
    # alegria 19.284 x nojo 444: raiz de 43 da 6,6, o teto segura em 4.
    assert repeticoes_por_classe([19284, 444, 4821]) == [1, 4, 2]
    assert repeticoes_por_classe([10, 0, 10]) == [1, 0, 1]


def test_probabilidades_de_emocao_saem_na_ordem_do_pacote():
    resposta = {"answers": {"emocao": {"probabilities": {
        nome: (0.4 if nome == "raiva" else 0.1) for nome in reversed(NOMES_EMOCOES)
    }}}}
    lidas = probabilidades_emocao(resposta)
    assert lidas[NOMES_EMOCOES.index("raiva")] == 0.4
    assert len(lidas) == len(NOMES_EMOCOES)


def test_probabilidade_de_emocao_faltando_levanta():
    resposta = {"answers": {"emocao": {"probabilities": {"alegria": 1.0}}}}
    with pytest.raises(KeyError):
        probabilidades_emocao(resposta)


def test_mapa_de_poda_manda_token_descartado_para_o_desconhecido():
    mapa, mantidos = mapa_de_poda({5, 2, 9}, tamanho=10, id_desconhecido=2)
    assert mantidos == [2, 5, 9]
    assert [mapa[2], mapa[5], mapa[9]] == [0, 1, 2]
    assert mapa[7] == mapa[2]  # fora do vocabulario podado vira desconhecido
    assert len(mapa) == 10


def test_mapa_de_poda_sempre_mantem_o_desconhecido():
    mapa, mantidos = mapa_de_poda({4}, tamanho=6, id_desconhecido=1)
    assert mantidos == [1, 4]
    assert mapa[0] == mapa[1] == 0
    with pytest.raises(ValueError):
        mapa_de_poda({8}, tamanho=6, id_desconhecido=1)
