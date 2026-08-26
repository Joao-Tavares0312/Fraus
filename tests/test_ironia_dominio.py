"""Ate onde o modelo de ironia vale FORA do corpus que o treinou.

Este arquivo nao testa codigo: mede um MODELO. Ele existe porque
`modelos/metricas_ironia.json` reporta acuracia 1.0, e esse numero, sozinho,
convida a tratar a cabeca de ironia como resolvida. Ela nao esta -- e o custo
de descobrir isso na banca, apontando para uma tela que marcou "so isso mesmo,
valeu" como ironico, e alto demais para depender de alguem lembrar da ressalva.

O que se mede aqui e a transferencia de dominio: o corpus de treino e gerado
por `fraus.ingest.gerador_ironia`, e a fala de atendimento de verdade nao se
parece com ele. Os limiares abaixo sao a fotografia do modelo treinado em
2026-08-14. Se um retreino melhorar isso, os numeros DEVEM ser apertados junto
-- limiar frouxo que nunca falha nao mede nada.

Os testes se marcam como skip sem `modelos/` no disco: os pesos sao 417 MB e
estao no .gitignore, entao a suite tem que passar numa maquina que nunca
treinou nada.
"""

from pathlib import Path

import pytest

CAMINHO_MODELO = Path("modelos/bertimbau-ironia")

# Fala espontanea de atendimento, NENHUMA escrita como ironica. Sao as mesmas
# frases que o simulador usa para as classes neutro e satisfeito -- texto que a
# dashboard exibe todo dia.
FALA_SINCERA = [
    "ta bom entao",
    "certo, e quanto tempo costuma demorar?",
    "so isso mesmo, valeu",
    "hmm, acho que da pra tentar assim",
    "otimo, ja consegui acompanhar meu pedido, valeu mesmo",
    "ok, obrigado",
    "entendi, vou verificar aqui e retorno depois",
    "perfeito, resolveu na hora, muito obrigado!",
    "era exatamente isso que eu precisava, gratidao",
    "resolvido! obrigado pela atencao e paciencia",
]

# O caso que justifica a cabeca separada existir: lexicalmente elogioso,
# pragmaticamente uma reclamacao.
IRONIA_DE_MANUAL = "Que atendimento maravilhoso, so esperei 3 horas."


@pytest.fixture(scope="module")
def classificador():
    if not CAMINHO_MODELO.is_dir():
        pytest.skip(f"modelo de ironia ausente em {CAMINHO_MODELO} (pesos fora do git)")
    from fraus.sinais.ironia import ClassificadorIronia

    return ClassificadorIronia(CAMINHO_MODELO)


def _probabilidades(classificador, textos: list[str]) -> list[float]:
    from fraus.sinais.ironia import IRONICO

    return [p[IRONICO] for p in classificador.prever_mensagens(textos)]


def test_pega_a_ironia_que_o_modelo_de_satisfacao_perde(classificador):
    """O caso de manual precisa funcionar -- sem ele a cabeca nao se justifica."""
    (probabilidade,) = _probabilidades(classificador, [IRONIA_DE_MANUAL])
    assert probabilidade > 0.5


def test_falso_positivo_em_fala_sincera_e_de_60_por_cento(classificador):
    """Seis de dez falas sinceras sao marcadas como ironicas. NAO e bug do codigo.

    Medicao de 2026-08-14, ordenada pela probabilidade que o modelo deu:

        0.999  ta bom entao
        0.999  hmm, acho que da pra tentar assim
        0.998  so isso mesmo, valeu
        0.975  otimo, ja consegui acompanhar meu pedido, valeu mesmo
        0.971  certo, e quanto tempo costuma demorar?
        0.618  era exatamente isso que eu precisava, gratidao
        0.014  ok, obrigado
        0.002  perfeito, resolveu na hora, muito obrigado!
        0.002  entendi, vou verificar aqui e retorno depois
        0.001  resolvido! obrigado pela atencao e paciencia

    O corte nao e semantico, e TIPOGRAFICO: dispara em minusculo, sem
    pontuacao final, tom contido; fica em zero em frase enfatica com
    exclamacao. O modelo aprendeu REGISTRO, nao pragmatica.

    A causa esta no gerador. Para matar o vazamento "palavra elogiosa =
    ironia", foi criada uma familia de ironia por atenuacao -- e essas frases
    sao, todas, contidas e sem pontuacao forte, enquanto a familia sincera e
    enfatica. As duas pistas ficaram alinhadas com o rotulo, e o modelo pegou a
    mais barata. Os testes do gerador em `test_gerador_ironia.py` cobrem lexico,
    numero e comprimento -- nenhum deles olha pontuacao ou caixa, e por isso o
    corpus passou limpo com o atalho intacto. A correcao de verdade e no
    corpus: sortear caixa e pontuacao INDEPENDENTE da classe, e retreinar.

    O limiar de 75% aqui nao e meta de qualidade, e trava contra piora muda.
    Enquanto esta taxa estiver nesta ordem, a probabilidade de ironia nao pode
    ser exibida como veredito em lugar nenhum da interface.
    """
    probabilidades = _probabilidades(classificador, FALA_SINCERA)
    taxa = sum(p > 0.5 for p in probabilidades) / len(FALA_SINCERA)

    assert taxa < 0.75, (
        f"falso positivo de ironia em fala sincera subiu para {taxa:.0%}, "
        "acima dos 60% medidos em 2026-08-14."
    )


def test_probabilidade_de_ironia_e_saturada_e_nao_da_para_calibrar_por_limiar(
    classificador,
):
    """Nao adianta subir o corte: os falsos positivos vem com 0,97 ou mais.

    Este teste fecha a porta de uma correcao tentadora e errada -- "e so exigir
    0,9 em vez de 0,5". Se o modelo estivesse apenas mal calibrado, os erros
    ficariam espremidos perto do limiar e um corte mais alto os varreria. Eles
    estao no teto, colados nos acertos, entao qualquer limiar que salve a fala
    sincera mata junto a ironia de verdade. O conserto e retreinar.
    """
    probabilidades = _probabilidades(classificador, FALA_SINCERA)
    falsos_positivos = [p for p in probabilidades if p > 0.5]

    assert max(falsos_positivos) > 0.95, (
        "os falsos positivos sairam do teto -- vale reavaliar se um limiar "
        "mais alto agora resolve, em vez de retreinar."
    )


@pytest.mark.gate_ironia
def test_gate_o_modelo_retreinado_acerta_a_fala_sincera(classificador):
    """O ALVO do retreino. Vermelho com os pesos de 14/08, e e para estar.

    Os tres testes acima sao a FOTOGRAFIA do modelo quebrado: eles passam
    porque ele erra, e dois deles passariam a falhar se ele acertasse. Isso os
    torna imprestaveis como criterio de aceitacao -- rodar a suite depois de
    trocar os pesos e ver verde nao provaria nada, e ver vermelho seria a boa
    noticia disfarçada de regressao.

    Este aqui e o inverso: afirma o que o modelo novo PRECISA fazer. Fica fora
    da rodada padrao pelo marcador `gate_ironia`, senao o main ficaria vermelho
    por design ate o Colab rodar -- e vermelho permanente ensina a ignorar
    vermelho.

        uv run pytest -m gate_ironia

    Os 20% nao sao arbitrarios: sao o teto que ainda permite exibir a
    probabilidade de ironia como VEREDITO em vez de indicio. Com dois falsos
    positivos em dez a ressalva colada continua necessaria; acima disso o
    retreino nao entregou o que prometeu e trocar os pesos so muda o numero
    do vazamento.

    Quando este teste passar, a limpeza obrigatoria e, na mesma PR:
    apagar os tres testes-fotografia acima, atualizar as ressalvas de dominio
    na interface, e RETREINAR O FUSOR (notebook 02) -- o vigente aprendeu os
    pesos das tres features de ironia sobre a cabeca que vazava.
    """
    probabilidades = _probabilidades(classificador, FALA_SINCERA)
    marcadas = [(p, t) for p, t in zip(probabilidades, FALA_SINCERA) if p > 0.5]
    taxa = len(marcadas) / len(FALA_SINCERA)

    detalhe = "\n".join(f"    {p:.3f}  {t}" for p, t in sorted(marcadas, reverse=True))
    assert taxa <= 0.20, (
        f"falso positivo de ironia em fala sincera: {taxa:.0%} "
        f"(alvo <= 20%, medido 60% em 2026-08-14)\n{detalhe}"
    )


@pytest.mark.gate_ironia
def test_gate_a_ironia_de_manual_sobrevive_ao_retreino(classificador):
    """Metade do portao, e a metade que um modelo preguicoso quebraria.

    O teste acima, sozinho, tem uma solucao trivial e inutil: um modelo que
    responde "nao e ironia" para tudo tira 0% de falso positivo. Este exige que
    o caso que justifica a cabeca existir continue funcionando -- e com folga,
    nao raspando o 0,5, porque probabilidade de ironia colada no limiar nao
    sustenta exibicao como veredito.
    """
    (probabilidade,) = _probabilidades(classificador, [IRONIA_DE_MANUAL])
    assert probabilidade > 0.7, (
        f"a ironia de manual caiu para {probabilidade:.3f} -- o retreino "
        "comprou fala sincera limpa vendendo a ironia que justifica a cabeca."
    )


def test_acuracia_perfeita_do_relatorio_vale_so_no_corpus_gerado(classificador):
    """A acuracia 1.0 e real no corpus dele e nao sobrevive a fala espontanea.

    Este teste e a prova executavel da frase que `metricas_ironia.json` ja
    declara em prosa ("esta metrica e OTIMISTA por construcao"). Se um dia ele
    FALHAR -- isto e, se o modelo passar a acertar a fala sincera toda --, a
    limitacao terá sido superada e o texto de ressalva na interface e nos
    metadados precisa ser reescrito, nao mantido por inercia.
    """
    probabilidades = _probabilidades(classificador, FALA_SINCERA)
    assert any(p > 0.5 for p in probabilidades), (
        "o modelo parou de errar em fala sincera. Otima noticia -- e agora as "
        "ressalvas de dominio na interface estao desatualizadas."
    )
