"""/modelo -- a ficha do que esta carregado, e o teste de uma frase avulsa.

Pesos globais, metricas de treino de cada cabeca, faixas vigentes e lexicon de
emoji. Metrica ausente vem `null`, nunca um numero inventado: "nao medimos" e
"medimos zero" sao respostas diferentes.

`/modelo/simular` roda o classificador numa frase digitada, sem tocar no
banco -- e onde a frase ironica se denuncia, saindo com prob_satisfeito alta E
prob_ironia alta ao mesmo tempo.

Analisar ARQUIVO e outro dominio: `rotas/analise.py`.
"""

from fastapi import APIRouter, Depends, HTTPException

from fraus.api.caminhos import (CAMINHO_METRICAS, CAMINHO_METRICAS_EMOCAO,
                                CAMINHO_METRICAS_IRONIA, metricas_de)
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoSimulacao
from fraus.sinais.emoji import linhas_lexicon, score_do_emoji
from fraus.sinais.emocao import NOMES_EMOCOES

# Teto de tamanho do texto aceito por /modelo/simular -- nao e limite de
# modelo (BERTimbau trunca em TAMANHO_MAXIMO tokens), e limite de payload.
TETO_TEXTO_SIMULACAO = 2000

# Teto de itens que /modelo/lexicon devolve por pagina, mesmo se pedirem mais.
TETO_LEXICON = 200

LIMITE_LEXICON_PADRAO = 50

router = APIRouter()


@router.get("/modelo")
def modelo(ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Ficha do modelo: pesos globais, metricas de treino, faixas e lexicon.

    `metricas` e null quando o notebook 01 ainda nao exportou o arquivo --
    nunca um valor inventado. As faixas de NPS saem da configuracao
    vigente, a MESMA fonte que alimenta a categoria de cada atendimento --
    faixa duplicada em dois lugares ja foi defeito deste projeto uma vez.
    """
    metricas = metricas_de(CAMINHO_METRICAS)
    return {
        "importancias": ctx.motor.importancias(),
        "metricas": metricas,
        "classes": ["insatisfeito", "neutro", "satisfeito"],
        # As tres cabecas, cada uma com a metrica que ela de fato mediu e a
        # limitacao que essa metrica esconde. `pontua` separa quem decide a
        # nota de quem so descreve: hoje so a satisfacao entra no fusor.
        "cabecas": [
            {
                "nome": "satisfacao",
                "classes": ["insatisfeito", "neutro", "satisfeito"],
                "metricas": metricas,
                "pontua": True,
            },
            {
                "nome": "emocao",
                "classes": [*NOMES_EMOCOES, "desprezo"],
                "metricas": metricas_de(CAMINHO_METRICAS_EMOCAO),
                "pontua": False,
            },
            {
                "nome": "ironia",
                "classes": ["nao-ironico", "ironico"],
                "metricas": metricas_de(CAMINHO_METRICAS_IRONIA),
                "pontua": False,
            },
        ],
        "faixas_nps": {
            categoria: list(faixa) for categoria, faixa in ctx.faixas_vigentes().items()
        },
        "total_emojis_lexicon": len(linhas_lexicon()),
    }


@router.get("/modelo/lexicon")
def lexicon(
    busca: str | None = None, limite: int = LIMITE_LEXICON_PADRAO, deslocamento: int = 0,
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Pagina o lexicon de emoji, ordenado por total de anotacoes.

    `score` reaproveita `score_do_emoji` -- a mesma fonte usada no sinal
    de emoji e na simulacao, para nunca divergir da formula real.
    """
    limite_efetivo = max(0, min(limite, TETO_LEXICON))
    deslocamento_efetivo = max(0, deslocamento)

    linhas = linhas_lexicon()
    if busca:
        linhas = [linha for linha in linhas if linha["emoji"] == busca]
    linhas_ordenadas = sorted(
        linhas,
        key=lambda linha: linha["negativo"] + linha["neutro"] + linha["positivo"],
        reverse=True,
    )
    pagina = linhas_ordenadas[deslocamento_efetivo:deslocamento_efetivo + limite_efetivo]

    return {
        "total": len(linhas_ordenadas),
        "itens": [
            {
                "emoji": linha["emoji"],
                "score": score_do_emoji(linha["emoji"]),
                "negativo": linha["negativo"],
                "neutro": linha["neutro"],
                "positivo": linha["positivo"],
            }
            for linha in pagina
        ],
    }


@router.post("/modelo/simular")
def simular(
    pedido: PedidoSimulacao, ctx: Contexto = Depends(obter_contexto)
) -> dict:
    """Roda o classificador numa frase avulsa -- nao persiste nada no banco."""
    texto = pedido.texto
    if not texto.strip():
        raise HTTPException(status_code=400, detail="texto vazio")
    if len(texto) > TETO_TEXTO_SIMULACAO:
        raise HTTPException(
            status_code=400,
            detail=f"texto acima do limite de {TETO_TEXTO_SIMULACAO} caracteres",
        )

    resultado = ctx.motor.simular_texto(texto)
    return {
        "texto": texto,
        "prob_insatisfeito": resultado["prob_insatisfeito"],
        "prob_neutro": resultado["prob_neutro"],
        "prob_satisfeito": resultado["prob_satisfeito"],
        "emojis": resultado["emojis"],
        "emocao": resultado.get("emocao"),
        "prob_ironia": resultado.get("prob_ironia"),
    }
