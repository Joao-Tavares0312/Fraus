from datetime import datetime, timezone

from fraus.modelos import Conversa, Mensagem
from fraus.sinais.lexico import (anotar_texto, features_lexico,
                                 polaridade_do_termo)

BASE = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)


def _conversa(textos: list[str], autor: str = "cliente") -> Conversa:
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=BASE,
        mensagens=[Mensagem(autor=autor, texto=t, enviada_em=BASE) for t in textos],
    )


def _polaridades(texto: str) -> dict[str, int]:
    return {termo: polaridade for termo, polaridade, _ in anotar_texto(texto)}


def test_lexicon_carrega_e_tem_as_duas_polaridades():
    assert polaridade_do_termo("otimo") == 1
    assert polaridade_do_termo("pessimo") == -1
    assert polaridade_do_termo("xyzabcnaoexiste") == 0


def test_termo_fora_do_lexicon_vale_zero_e_nao_quebra():
    assert anotar_texto("blergh flurb") == []


def test_acento_ausente_ainda_acha_o_termo():
    """Cliente de chat digita 'otimo'; o SentiLex guarda 'otimo' com acento."""
    assert polaridade_do_termo("ótimo") == polaridade_do_termo("otimo") == 1
    assert polaridade_do_termo("péssimo") == polaridade_do_termo("pessimo") == -1


def test_verbo_de_afeto_e_neutro_no_sentilex():
    """Limitacao declarada do recurso, nao bug.

    O SentiLex e lexicon de JULGAMENTO SOCIAL: anota polaridade dirigida a
    entidade humana. Verbo de afeto do proprio falante vale 0 nele -- quem le
    'adorei o produto' e o BERTimbau, nao o lexicon.
    """
    assert polaridade_do_termo("gostar") == 0
    assert polaridade_do_termo("adorei") == 0
    assert polaridade_do_termo("odiei") == 0


def test_negacao_inverte_a_polaridade_do_termo_seguinte():
    """O erro classico de lexicon: ler 'nao foi otimo' como positivo."""
    achados = anotar_texto("nao foi otimo o atendimento")
    negados = [(t, p) for t, p, negado in achados if negado]
    assert negados, "nenhum termo foi marcado como negado"
    assert all(p <= 0 for _, p in negados)


def test_negacao_nao_atravessa_pontuacao_forte():
    """'nao chegou. otimo atendimento' -- o otimo continua otimo."""
    achados = anotar_texto("nao chegou. otimo atendimento")
    por_termo = {t: (p, n) for t, p, n in achados}
    assert "otimo" in por_termo
    polaridade, negado = por_termo["otimo"]
    assert not negado
    assert polaridade == 1


def test_negacao_tem_alcance_limitado():
    """Longe demais do 'nao', o termo nao e negado."""
    texto = "nao sei um dois tres quatro cinco otimo"
    por_termo = {t: n for t, _, n in anotar_texto(texto)}
    assert por_termo.get("otimo") is False


def test_polaridade_media_negativa_em_reclamacao():
    features = features_lexico(_conversa(["atendimento pessimo e horrivel"]))
    assert features["lexico_polaridade_media"] < 0


def test_polaridade_media_positiva_em_elogio():
    features = features_lexico(_conversa(["atendimento otimo e excelente"]))
    assert features["lexico_polaridade_media"] > 0


def test_negacao_vira_a_media_do_elogio():
    """Mesmas palavras positivas, com 'nao' na frente: a media tem que virar."""
    elogio = features_lexico(_conversa(["foi otimo"]))
    negado = features_lexico(_conversa(["nao foi otimo"]))
    assert negado["lexico_polaridade_media"] < elogio["lexico_polaridade_media"]
    assert negado["lexico_frac_negados"] > 0


def test_cobertura_conta_quanta_evidencia_lexical_existe():
    pouca = features_lexico(_conversa(["o pedido chegou na terca de manha no endereco otimo"]))
    muita = features_lexico(_conversa(["otimo excelente maravilhoso"]))
    assert muita["lexico_cobertura"] > pouca["lexico_cobertura"]
    assert 0.0 <= pouca["lexico_cobertura"] <= 1.0


def test_conversa_sem_fala_do_cliente_zera_as_features():
    features = features_lexico(_conversa(["otimo"], autor="bot"))
    assert features == {
        "lexico_polaridade_media": 0.0,
        "lexico_frac_negados": 0.0,
        "lexico_cobertura": 0.0,
    }


def test_texto_sem_termo_do_lexicon_nao_divide_por_zero():
    features = features_lexico(_conversa(["blergh flurb zzz"]))
    assert features["lexico_polaridade_media"] == 0.0
    assert features["lexico_cobertura"] == 0.0


# --- A CURADORIA -----------------------------------------------------------
# O que o analista ensinou ao lexico. Ver fraus/sinais/curadoria.py.

from fraus.sinais.curadoria import Curadoria  # noqa: E402


def test_curadoria_preenche_buraco_do_lexicon():
    """Termo ausente do SentiLex passa a valer o que o analista disse."""
    assert polaridade_do_termo("lentissimo") == 0  # hoje: desconhecido vale 0
    c = Curadoria(palavras={"lentissimo": -1})
    assert polaridade_do_termo("lentissimo", c) == -1


def test_curadoria_VENCE_o_lexicon_base():
    """Nao e so preencher buraco: e corrigir polaridade errada de dominio."""
    assert polaridade_do_termo("otimo") == 1
    c = Curadoria(palavras={"otimo": -1})
    assert polaridade_do_termo("otimo", c) == -1


def test_curado_como_zero_SILENCIA_o_termo():
    assert polaridade_do_termo("otimo") == 1
    c = Curadoria(palavras={"otimo": 0})
    assert polaridade_do_termo("otimo", c) == 0


def test_curadoria_alcanca_o_termo_sem_acento():
    """O cliente de chat nem sempre acentua, e o lexico ja trata isso com um
    indice de reserva. A curadoria entra na MESMA busca, senao a palavra curada
    com acento sumiria quando digitada sem."""
    c = Curadoria(palavras={"lentíssimo": -1})
    assert polaridade_do_termo("lentissimo", c) == -1


def test_negacao_continua_valendo_sobre_termo_curado():
    c = Curadoria(palavras={"lentissimo": -1})
    achados = anotar_texto("nao ficou lentissimo", c)
    assert ("lentissimo", 1, True) in achados


def test_ngrama_curado_vence_o_token_solto():
    """A curadoria entra no mesmo ponto da busca de n-gramas, entao um termo
    curado de duas palavras vence o token que o compoe -- igual a um idioma do
    SentiLex."""
    c = Curadoria(palavras={"fora do ar": -1, "ar": 1})
    achados = anotar_texto("o sistema ficou fora do ar", c)
    assert ("fora do ar", -1, False) in achados
    assert all(termo != "ar" for termo, _, _ in achados)


def test_curadoria_move_as_features():
    c = Curadoria(palavras={"lentissimo": -1})
    conversa = _conversa(["o app ta lentissimo"])
    sem = features_lexico(conversa)
    com = features_lexico(conversa, c)
    assert sem["lexico_cobertura"] == 0.0
    assert com["lexico_cobertura"] > 0.0
    assert com["lexico_polaridade_media"] == -1.0


def test_sem_curadoria_o_comportamento_e_o_de_antes():
    """A garantia de que esta mudanca nao mexeu no que ja funcionava."""
    conversa = _conversa(["o atendimento foi otimo"])
    assert features_lexico(conversa) == features_lexico(conversa, None)
