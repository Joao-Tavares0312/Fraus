"""Testes do gerador de ironia sintetica.

O grosso daqui nao verifica formato: verifica que o corpus NAO VAZA o
gabarito. Corpus sintetico com atalho e pior que corpus nenhum -- ele produz
metrica alta e modelo inutil, que foi exatamente o que aconteceu com o
primeiro fusor (99,3% no sintetico, ~50 para tudo em conversa real).
"""

import pytest

from fraus.ingest.gerador_ironia import (ELOGIOS, FATOS_RUINS, MARCADORES,
                                         NEUTRAS, gerar_exemplos)
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


def test_marcador_de_discurso_nao_separa_as_classes():
    """O vazamento que os outros testes deixaram passar, e que custou um treino.

    Marcador conversacional ("olha", "entao", "poxa", "bom") abria as dezoito
    ATENUACOES e nao aparecia em nenhuma familia sincera. Nenhum teste olhava
    para isso -- os outros caçam lexico de elogio, numero e comprimento -- e o
    corpus passou limpo com o atalho intacto. O modelo treinado nele leu
    "marcador = ironia" e marcou "ta bom entao" como ironico com 0,999 de
    confianca, o que esta medido em tests/test_ironia_dominio.py.

    A trava e por PROPORCAO nas duas classes, nao por presenca: exigir apenas
    "existe marcador na classe sincera" passaria com um unico exemplo entre
    tres mil, e um marcador raro de um lado e frequente do outro continua
    prevendo o rotulo. A diferenca entre as duas taxas e o que precisa ser
    pequena.
    """
    exemplos = gerar_exemplos(1200, semente=17)

    def tem_marcador(texto: str) -> bool:
        return any(texto.lower().startswith(m.lower() + ",") for m in MARCADORES)

    taxa_ironica = _proporcao(exemplos, IRONICO, tem_marcador)
    taxa_sincera = _proporcao(exemplos, NAO_IRONICO, tem_marcador)

    assert taxa_sincera > 0.15, (
        f"marcador de discurso quase nao aparece na classe sincera "
        f"({taxa_sincera:.1%}) -- ele voltou a ser gabarito de ironia."
    )
    assert abs(taxa_ironica - taxa_sincera) < 0.12, (
        f"marcador aparece em {taxa_ironica:.1%} da ironia contra "
        f"{taxa_sincera:.1%} da fala sincera: a diferenca prevê o rotulo."
    )


def test_caixa_e_pontuacao_nao_separam_as_classes():
    """A pista TIPOGRAFICA -- a que o modelo de 14/08 de fato leu.

    O teste do marcador acima nomeia a causa do vazamento, mas a medicao em
    tests/test_ironia_dominio.py descreve o corte observado como outra coisa:
    "dispara em minusculo, sem pontuacao final, tom contido; fica em zero em
    frase enfatica com exclamacao". Isso e caixa e pontuacao, nao marcador.

    `_talvez_maiuscula` ja aplica as duas por sorteio no gargalo unico de
    `acrescentar`, junto com marcador e emoji -- a correcao existe. O que nao
    existia era teste olhando para ela, que e exatamente a historia do
    marcador se repetindo: a defesa entra no codigo, ninguem tranca, e o
    proximo refactor que mover um sorteio para dentro de um ramo especifico
    recria o vazamento em silencio. O corpus volta a passar limpo e a conta
    chega tres horas depois, na metrica.

    Trava por PROPORCAO nas duas classes, como a do marcador: maiuscula rara
    de um lado e comum do outro continua prevendo o rotulo, mesmo que as duas
    classes tenham algum exemplo de cada forma.
    """
    exemplos = gerar_exemplos(1200, semente=19)

    def comeca_em_maiuscula(texto: str) -> bool:
        return bool(texto) and texto[0].isupper()

    def termina_com_pontuacao(texto: str) -> bool:
        return texto.rstrip().endswith((".", "!", "..."))

    for nome, pista in (
        ("caixa alta na abertura", comeca_em_maiuscula),
        ("pontuacao final", termina_com_pontuacao),
    ):
        taxa_ironica = _proporcao(exemplos, IRONICO, pista)
        taxa_sincera = _proporcao(exemplos, NAO_IRONICO, pista)

        assert min(taxa_ironica, taxa_sincera) > 0.05, (
            f"{nome} quase nao aparece numa das classes "
            f"(ironica {taxa_ironica:.1%}, sincera {taxa_sincera:.1%}) -- "
            "voltou a ser gabarito."
        )
        assert abs(taxa_ironica - taxa_sincera) < 0.12, (
            f"{nome} aparece em {taxa_ironica:.1%} da ironia contra "
            f"{taxa_sincera:.1%} da fala sincera: a diferenca prevê o rotulo. "
            "E a pista que derrubou o modelo de 2026-08-14."
        )


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


def test_pedido_grande_nao_repete_nem_trava():
    """Cem mil exemplos saem unicos e em tempo de teste.

    Este numero ja foi maior que o espaco inteiro de combinacoes. Deixou de
    ser quando os marcadores de discurso entraram: o espaco pulou de menos de
    100 mil para 512.910 textos distintos. A garantia de ESGOTAMENTO mudou de
    endereco -- foi para o teste marcado como `lento` logo abaixo, que e o
    unico que consegue prova-la de fato.
    """
    exemplos = gerar_exemplos(100_000, semente=5)
    textos = [t.lower().strip() for t, _ in exemplos]
    assert len(textos) == len(set(textos))
    assert len(exemplos) == 100_000


@pytest.mark.lento
def test_pedido_alem_do_espaco_devolve_o_que_da_sem_travar():
    """Pedido impossivel para por ESGOTAMENTO, sem repetir e sem laco infinito.

    Fica fora da suite padrao (`-m "not lento"`) porque exaurir as 512.910
    combinacoes leva pouco mais de tres minutos -- custo que nao cabe em cada
    rodada, mas que tambem nao pode simplesmente deixar de existir: e o unico
    teste que exercita a condicao de parada por PACIENCIA. Rode com
    `uv run pytest -m lento` ao mexer no gerador.

    O limite inferior de 400 mil e frouxo de proposito. Ele existe para pegar
    um gerador que passou a esgotar cedo demais (sinal de familia de frase
    perdida no caminho), nao para fixar o tamanho exato do espaco, que muda de
    forma legitima toda vez que um molde novo entra.
    """
    exemplos = gerar_exemplos(5_000_000, semente=5)
    textos = [t.lower().strip() for t, _ in exemplos]
    assert len(textos) == len(set(textos))
    assert 400_000 < len(exemplos) < 5_000_000
