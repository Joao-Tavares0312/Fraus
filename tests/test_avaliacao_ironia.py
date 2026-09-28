import pytest

from fraus.avaliacao_ironia import (IRONIAS_SEM_MARCADOR,
                                     SINCERAS_COM_MARCADOR,
                                     avaliar_classificador,
                                     avaliar_probabilidades,
                                     candidato_apto_para_promocao)


def test_regua_tem_duas_fatias_balanceadas_e_sem_sobreposicao():
    assert len(SINCERAS_COM_MARCADOR) == len(IRONIAS_SEM_MARCADOR) == 10
    assert set(SINCERAS_COM_MARCADOR).isdisjoint(IRONIAS_SEM_MARCADOR)


def test_avaliacao_conta_os_dois_erros_e_a_confianca_errada():
    resultado = avaliar_probabilidades([0.1, 0.9], [0.8, 0.2])
    assert resultado.falsos_positivos == 1
    assert resultado.falsos_negativos == 1
    assert resultado.taxa_falso_positivo == pytest.approx(0.5)
    assert resultado.taxa_falso_negativo == pytest.approx(0.5)
    assert resultado.maior_confianca_errada == pytest.approx(0.9)


def test_avaliacao_recusa_probabilidade_invalida_e_fatia_vazia():
    with pytest.raises(ValueError, match="0..1"):
        avaliar_probabilidades([1.1], [0.5])
    with pytest.raises(ValueError, match="sinceros e ironicos"):
        avaliar_probabilidades([], [0.5])


def test_portao_reprova_modelo_que_so_acerta_uma_fatia():
    resultado = avaliar_probabilidades([0.1] * 10, [0.1] * 10)
    assert candidato_apto_para_promocao(resultado) is False


def test_portao_aprova_candidato_abaixo_dos_limites_nas_duas_fatias():
    resultado = avaliar_probabilidades([0.1] * 8 + [0.9] * 2, [0.9] * 8 + [0.1] * 2)
    assert candidato_apto_para_promocao(resultado) is True


def test_avaliador_aceita_o_contrato_dos_classificadores():
    class ClassificadorPerfeito:
        def prever_mensagens(self, textos):
            return [[0.9, 0.1] if t in SINCERAS_COM_MARCADOR else [0.1, 0.9] for t in textos]

    resultado = avaliar_classificador(ClassificadorPerfeito())
    assert resultado.falsos_positivos == resultado.falsos_negativos == 0
