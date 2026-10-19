"""Leitores de corpus compartilhados por notebooks e benchmark.

Quem treina e quem mede leem o corpus pelo MESMO codigo; senao a impressao
do teste diverge e a comparacao nao vale.
"""

from __future__ import annotations

import csv
import io
import zipfile

import pytest

from fraus.corpora import (
    Exemplos,
    ler_b2w,
    ler_consumerbr,
    ler_xed_pt,
    rotulo_por_estrelas,
)


def test_rotulo_por_estrelas_segue_a_ordem_das_classes():
    # invariante 8: 0 insatisfeito, 1 neutro, 2 satisfeito
    assert [rotulo_por_estrelas(n) for n in (1, 2, 3, 4, 5)] == [0, 0, 1, 2, 2]


@pytest.mark.parametrize("nota", [0, 6, None, "x", 2.5])
def test_rotulo_por_estrelas_recusa_nota_fora_da_escala(nota):
    assert rotulo_por_estrelas(nota) is None


def _b2w(tmp_path):
    caminho = tmp_path / "b2w.csv"
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "review_text", "overall_rating", "reviewer_id"])
        w.writerow(["p1", "Chegou quebrado, péssimo", "1", "r1"])
        w.writerow(["p1", "Mediano, ok", "3", "r2"])
        w.writerow(["p2", 'Excelente, "recomendo", top', "5", "r3"])
        w.writerow(["p3", "", "4", "r4"])  # sem texto: sai
        w.writerow(["p4", "nota invalida", "", "r5"])  # sem nota: sai
    return caminho


def test_ler_b2w_rotula_e_agrupa_por_produto(tmp_path):
    ex = ler_b2w(_b2w(tmp_path))
    assert isinstance(ex, Exemplos)
    assert ex.textos == ["Chegou quebrado, péssimo", "Mediano, ok", 'Excelente, "recomendo", top']
    assert ex.rotulos == [0, 1, 2]
    assert ex.grupos == ["p1", "p1", "p2"]
    assert ex.nomes_classes == ["insatisfeito", "neutro", "satisfeito"]


def _consumerbr(tmp_path):
    texto = io.StringIO()
    w = csv.writer(texto)
    w.writerow([
        "empresa", "reclamacao_labeled", "resposta_labeled", "padronizada", "status",
        "data_abertura", "localizacao", "data_resposta", "avaliacao_nota",
        "avaliacao_comentario",
    ])
    w.writerow(["A", "cobraram duas vezes", "resolvido", "False", "Resolvida", "", "", "", "Nota 5",
                "Resolveram rápido, obrigado"])
    w.writerow(["B", "nao entregaram", "aguarde", "True", "Não Resolvida", "", "", "", "Nota 1",
                "Ninguém resolveu nada"])
    w.writerow(["A", "x", "y", "False", "Resolvida", "", "", "", "Nota 3", "Mais ou menos"])
    w.writerow(["C", "z", "w", "False", "Resolvida", "", "", "", "Nota 4", ""])  # sem comentario
    w.writerow(["C", "z", "w", "False", "Resolvida", "", "", "", "", "sem nota"])
    caminho = tmp_path / "ConsumerBR.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("ConsumerBR/consumerbr.csv", texto.getvalue())
    return caminho


def test_ler_consumerbr_usa_o_comentario_da_avaliacao_e_nao_a_reclamacao(tmp_path):
    # A reclamacao e escrita ANTES da resolucao: quase sempre negativa, e a
    # nota mede o desfecho. O texto que acompanha a nota e o comentario.
    ex = ler_consumerbr(_consumerbr(tmp_path))
    assert ex.textos == ["Resolveram rápido, obrigado", "Ninguém resolveu nada", "Mais ou menos"]
    assert ex.rotulos == [2, 0, 1]
    assert ex.grupos == ["A", "B", "A"]


def test_nota_do_consumerbr_vem_como_texto():
    from fraus.corpora import nota_consumerbr

    assert nota_consumerbr("Nota 4") == 4
    assert nota_consumerbr(" nota 1 ") == 1
    assert nota_consumerbr("") is None and nota_consumerbr("Nota") is None


def test_ler_consumerbr_respeita_limite(tmp_path):
    assert len(ler_consumerbr(_consumerbr(tmp_path), limite=2).textos) == 2


def test_ler_xed_pt_mapeia_plutchik_para_ekman_e_descarta_ambiguo(tmp_path):
    caminho = tmp_path / "pt.tsv"
    caminho.write_text(
        "Estou furioso\t1\n"           # anger -> raiva
        "Que alegria\t5\n"             # joy -> alegria
        "Espero que venha\t2\n"        # anticipation: sem par, sai
        "Tenho medo e nojo\t3,4\n"     # duas classes: sai
        "Que nojo\t3, 3\n",            # repetida, uma classe so: fica
        encoding="utf-8",
    )
    ex = ler_xed_pt(caminho)
    nomes = ex.nomes_classes
    assert ex.textos == ["Estou furioso", "Que alegria", "Que nojo"]
    assert [nomes[r] for r in ex.rotulos] == ["raiva", "alegria", "nojo"]


_EMOCOES_FINAS = [
    "admiration", "amusement", "anger", "annoyance", "approval", "caring", "confusion",
    "curiosity", "desire", "disappointment", "disapproval", "disgust", "embarrassment",
    "excitement", "fear", "gratitude", "grief", "joy", "love", "nervousness", "optimism",
    "pride", "realization", "relief", "remorse", "sadness", "surprise", "neutral",
]
_MAPA_EKMAN = {
    "anger": ["anger", "annoyance", "disapproval"], "disgust": ["disgust"],
    "fear": ["fear", "nervousness"],
    "joy": ["joy", "amusement", "approval", "excitement", "gratitude", "love", "optimism",
            "relief", "pride", "admiration", "desire", "caring"],
    "sadness": ["sadness", "disappointment", "embarrassment", "grief", "remorse"],
    "surprise": ["surprise", "realization", "confusion", "curiosity"],
}


def _goemotions(tmp_path, anotacoes):
    caminho = tmp_path / "ge.csv"
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text", "id", "author", "example_very_unclear", *_EMOCOES_FINAS, "texto"])
        for ident, autor, obscuro, marcadas, texto in anotacoes:
            w.writerow([texto, ident, autor, obscuro,
                        *[int(e in marcadas) for e in _EMOCOES_FINAS], texto])
    return caminho


def test_ler_goemotions_conta_votos_por_id_e_reduz_a_ekman(tmp_path):
    from fraus.corpora import ler_goemotions_ptbr

    caminho = _goemotions(tmp_path, [
        # dois anotadores em "gratitude" -> alegria
        ("a", "u1", "False", {"gratitude"}, "Valeu demais"),
        ("a", "u1", "False", {"gratitude", "anger"}, "Valeu demais"),
        # um voto so: nao passa do limiar
        ("b", "u2", "False", {"fear"}, "Que susto"),
        ("b", "u2", "False", set(), "Que susto"),
        # duas classes Ekman acima do limiar: sai
        ("c", "u3", "False", {"anger", "joy"}, "Misturado"),
        ("c", "u3", "False", {"anger", "joy"}, "Misturado"),
        # obscuro: a linha nao conta
        ("d", "u4", "True", {"neutral"}, "Hã"),
        ("d", "u4", "True", {"neutral"}, "Hã"),
        ("e", "u5", "False", {"neutral"}, "Tanto faz"),
        ("e", "u5", "False", {"neutral"}, "Tanto faz"),
    ])
    ex = ler_goemotions_ptbr([caminho], _MAPA_EKMAN)
    assert ex.textos == ["Valeu demais", "Tanto faz"]
    assert [ex.nomes_classes[r] for r in ex.rotulos] == ["alegria", "neutro"]
    assert ex.grupos == ["u1", "u5"]


def test_ler_multipico_vota_por_par_descarta_empate_e_agrupa_por_post(tmp_path):
    from fraus.corpora import ler_multipico

    caminho = tmp_path / "mp.csv"
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "source", "reply", "post", "language", "language_variety",
                    "annotator_id", "reply_id", "post_id"])
        for anot, rot in (("a1", "1"), ("a2", "1"), ("a3", "0")):      # maioria ironica
            w.writerow([rot, "reddit", "Que otimo, de novo", "Caiu o sistema", "pt", "br", anot, "r1", "p1"])
        for anot, rot in (("a1", "1"), ("a2", "0")):                    # empate: sai
            w.writerow([rot, "twitter", "Pode ser", "Vai chover?", "pt", "br", anot, "r2", "p2"])
        for anot, rot in (("a1", "0"), ("a2", "0")):                    # outra lingua: sai
            w.writerow([rot, "twitter", "Sure", "Q", "en", "us", anot, "r3", "p3"])
        for anot, rot in (("a1", "0"), ("a2", "0"), ("a3", "1")):      # maioria nao ironica
            w.writerow([rot, "twitter", "Obrigado pela dica", "Use o app", "pt", "pt", anot, "r4", "p1"])
    ex = ler_multipico(caminho)
    assert ex.textos == ["Que otimo, de novo", "Obrigado pela dica"]
    assert ex.rotulos == [1, 0]
    assert ex.grupos == ["p1", "p1"]
    assert ex.nomes_classes == ["nao_ironico", "ironico"]
    assert ler_multipico(caminho, variedade="br").textos == ["Que otimo, de novo"]
