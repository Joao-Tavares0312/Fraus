"""Testes do gerador de ironia sintetica.

O grosso daqui nao verifica formato: verifica que o corpus NAO VAZA o
gabarito. Corpus sintetico com atalho e pior que corpus nenhum -- ele produz
metrica alta e modelo inutil, que foi exatamente o que aconteceu com o
primeiro fusor (99,3% no sintetico, ~50 para tudo em conversa real).
"""

import pytest

from fraus.ingest.gerador_ironia import (ELOGIOS, FATOS_RUINS, NEUTRAS,
                                         gerar_exemplos)
from fraus.sinais.ironia import IRONICO, NAO_IRONICO


def _proporcao(exemplos, rotulo, criterio):
    """Fracao dos exemplos de `rotulo` que satisfazem `criterio`."""
    da_classe = [t for t, r in exemplos if r == rotulo]
    assert da_classe, f"nenhum exemplo do rotulo {rotulo}"
    return sum(1 for t in da_classe if criterio(t)) / len(da_classe)


def test_mesma_semente_gera_o_mesmo_corpus():
    assert gerar_exemplos(200, semente=7) == gerar_exemplos(200, semente=7)


def test_sementes_diferentes_geram_corpora_diferentes():
    assert gerar_exemplos(200, semente=7) != gerar_exemplos(200, semente=8)


def test_corpus_e_equilibrado_entre_as_duas_classes():
    exemplos = gerar_exemplos(400, semente=1)
    ironicos = sum(1 for _, r in exemplos if r == IRONICO)
    assert ironicos == pytest.approx(len(exemplos) / 2, rel=0.15)


def test_nao_repete_texto():
    exemplos = gerar_exemplos(400, semente=3)
    textos = [t.lower().strip() for t, _ in exemplos]
    assert len(textos) == len(set(textos))


def test_so_existem_os_dois_rotulos():
    assert {r for _, r in gerar_exemplos(200, semente=2)} == {NAO_IRONICO, IRONICO}


# --- os testes que importam: ausencia de atalho ----------------------------


def test_fato_ruim_sozinho_nao_separa_as_classes():
    """O VAZAMENTO OBVIO. Se so a ironia citasse fato ruim, o modelo leria
    "reclamou de algo -> ironia" e nunca olharia a incongruencia."""
    exemplos = gerar_exemplos(600, semente=11)

    def tem_fato_ruim(texto: str) -> bool:
        baixo = texto.lower()
        return any(f.split()[0] in baixo for f in FATOS_RUINS)

    nas_ironicas = _proporcao(exemplos, IRONICO, tem_fato_ruim)
    nas_outras = _proporcao(exemplos, NAO_IRONICO, tem_fato_ruim)

    # Um classificador que respondesse so por esta pista precisa errar muito.
    assert nas_outras > 0.25, (
        f"fato ruim aparece em {nas_outras:.0%} das nao-ironicas -- baixo demais, "
        "vira atalho para o rotulo"
    )
    assert nas_ironicas > 0.9


def test_lexico_positivo_sozinho_nao_separa_as_classes():
    """Elogio precisa aparecer FORA da ironia -- no elogio sincero e no
    agradecimento que abre reclamacao."""
    exemplos = gerar_exemplos(600, semente=12)

    def tem_elogio(texto: str) -> bool:
        baixo = texto.lower()
        return any(e.split()[0] in baixo for e in ELOGIOS)

    assert _proporcao(exemplos, NAO_IRONICO, tem_elogio) > 0.2


def test_ironia_nao_exige_palavra_elogiosa():
    """A familia por atenuacao ("imagina, ... nao incomoda nada") existe para
    que "tem elogio" nao seja condicao NECESSARIA de ironia."""
    exemplos = gerar_exemplos(600, semente=13)

    def sem_elogio(texto: str) -> bool:
        baixo = texto.lower()
        return not any(e.split()[0] in baixo for e in ELOGIOS)

    assert _proporcao(exemplos, IRONICO, sem_elogio) > 0.1


def test_numero_aparece_nas_duas_classes():
    """Digito nao pode virar pista: ha numero no fato ruim e no fato bom."""
    exemplos = gerar_exemplos(600, semente=14)
    tem_digito = lambda t: any(c.isdigit() for c in t)  # noqa: E731
    assert _proporcao(exemplos, IRONICO, tem_digito) > 0.1
    assert _proporcao(exemplos, NAO_IRONICO, tem_digito) > 0.1


def test_comprimento_nao_separa_as_classes():
    """Se a ironia fosse sistematicamente mais longa, o modelo contaria
    caracteres em vez de ler."""
    exemplos = gerar_exemplos(600, semente=15)
    medias = {
        rotulo: sum(len(t) for t, r in exemplos if r == rotulo)
        / max(1, sum(1 for _, r in exemplos if r == rotulo))
        for rotulo in (NAO_IRONICO, IRONICO)
    }
    maior, menor = max(medias.values()), min(medias.values())
    assert maior / menor < 1.6, f"comprimento medio destoa: {medias}"


def test_a_nao_ironia_tem_as_tres_familias():
    """Elogio sincero, reclamacao direta e fala operacional. Sem a operacional,
    "nao tem carga emocional" viraria atalho."""
    exemplos = gerar_exemplos(600, semente=16)
    nao_ironicas = [t.lower() for t, r in exemplos if r == NAO_IRONICO]

    operacionais = sum(
        1 for t in nao_ironicas if any(n.split()[0] in t for n in NEUTRAS)
    )
    assert operacionais > 0, "nenhuma fala operacional entre as nao-ironicas"


def test_quantidade_pedida_e_respeitada():
    assert len(gerar_exemplos(150, semente=4)) == 150


def test_pedido_grande_demais_devolve_o_que_da_sem_travar():
    """O espaco de combinacoes e finito: melhor devolver menos que repetir ou
    entrar em laco infinito."""
    exemplos = gerar_exemplos(100_000, semente=5)
    textos = [t.lower().strip() for t, _ in exemplos]
    assert len(textos) == len(set(textos))
    assert len(exemplos) < 100_000
