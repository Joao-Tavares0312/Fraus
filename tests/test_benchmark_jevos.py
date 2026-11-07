"""A leitura da resposta do jevos nao pode inverter a ordem das classes."""

import pytest

from scripts.benchmark_jevos import probabilidades_do_jevos


def _resposta_satisfacao(probabilidades: dict) -> dict:
    return {"answers": {"sat": {"type": "choice", "probabilities": probabilidades}}}


def test_satisfacao_e_mapeada_por_nome_e_nao_pela_ordem_do_json():
    # JSON em ordem invertida: a lista sai 0 insatisfeito, 1 neutro, 2 satisfeito.
    resposta = _resposta_satisfacao({"satisfeito": 0.7, "neutro": 0.2, "insatisfeito": 0.1})
    assert probabilidades_do_jevos(resposta, "satisfacao") == [0.1, 0.2, 0.7]


def test_satisfacao_sem_uma_das_chaves_falha_alto():
    resposta = _resposta_satisfacao({"satisfeito": 0.7, "insatisfeito": 0.3})
    with pytest.raises(KeyError):
        probabilidades_do_jevos(resposta, "satisfacao")


def test_ironia_devolve_nao_ironico_e_ironico():
    resposta = {"answers": {"ironia": {"type": "noul", "noul": 0.8}}}
    assert probabilidades_do_jevos(resposta, "ironia") == pytest.approx([0.2, 0.8])
