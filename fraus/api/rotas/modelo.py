"""/modelo -- a ficha do que esta carregado, e o teste de uma frase avulsa.

Pesos globais, metricas de treino de cada cabeca, faixas vigentes e lexicon de
emoji. Metrica ausente vem `null`, nunca um numero inventado: "nao medimos" e
"medimos zero" sao respostas diferentes.

`/modelo/simular` roda o classificador numa frase digitada, sem tocar no
banco -- e onde a frase ironica se denuncia, saindo com prob_satisfeito alta E
prob_ironia alta ao mesmo tempo.

Analisar ARQUIVO e outro dominio: `rotas/analise.py`.
"""

import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from fraus.api.caminhos import (CAMINHO_COMPARACAO,
                                CAMINHO_COMPARACAO_PUBLICADA, CAMINHO_METRICAS,
                                CAMINHO_METRICAS_EMOCAO,
                                CAMINHO_METRICAS_IRONIA, CAMINHO_ONNX_LAYA,
                                backend_declarado, backend_ironia_declarado,
                                metricas_de)
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoSimulacao, PedidoSimulacaoIroniaLaya
from fraus.sinais.emoji import linhas_lexicon, score_do_emoji
from fraus.comparacao_modelos import relatorio_markdown, validar_laudo
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
        # nota de quem so descreve. Entre 21/08/2026 e 03/09/2026 as tres
        # entravam no fusor e marcavam True. Em 04/09/2026 a ironia SAIU do
        # vetor (ver `fraus/fusor.py`, comentario de `NOMES_FEATURES`): ela
        # continua carregada e lida por mensagem, mas nao decide mais a nota --
        # e exatamente o caso que este campo existe para distinguir.
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
                "pontua": True,
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
        "estilo": resultado.get("estilo"),
    }


@router.get("/modelo/ironia-laya")
def ficha_ironia_laya() -> dict:
    """Contrato da aba experimental; não carrega nem baixa o checkpoint."""
    from fraus.sinais.ironia_laya import revisao_laya_declarada

    return {
        "modelo": "convaiinnovations/laya",
        "checkpoint": "multilingual",
        "revisao": revisao_laya_declarada(),
        "classes": ["nao-ironico", "ironico"],
        "backend_ativo": backend_ironia_declarado() in {"laya", "laya-onnx"},
        "executor": backend_ironia_declarado(),
        "pontua": False,
    }


@router.post("/modelo/ironia-laya/simular")
def simular_ironia_laya(pedido: PedidoSimulacaoIroniaLaya) -> dict:
    """Roda somente o Laya; não carrega satisfação, emoção nem fusor."""
    texto = pedido.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="texto vazio")
    if len(texto) > TETO_TEXTO_SIMULACAO:
        raise HTTPException(
            status_code=400,
            detail=f"texto acima do limite de {TETO_TEXTO_SIMULACAO} caracteres",
        )
    from fraus.sinais.ironia_laya import (
        obter_classificador_ironia_laya_declarado, revisao_laya_declarada)

    ironico = obter_classificador_ironia_laya_declarado().prever_configurado(
        texto,
        contexto=pedido.contexto,
        instrucao=pedido.instrucao,
        criterio_ironico=pedido.criterio_ironico,
        criterio_literal=pedido.criterio_literal,
    )
    nao_ironico = 1.0 - ironico
    confianca = max(ironico, nao_ironico)
    if confianca < pedido.confianca_minima:
        classe = "inconclusivo"
    else:
        classe = "ironico" if ironico >= pedido.limiar else "nao-ironico"
    return {
        "texto": texto,
        "classe": classe,
        "prob_nao_ironico": nao_ironico,
        "prob_ironia": ironico,
        "confianca": confianca,
        "limiar": pedido.limiar,
        "confianca_minima": pedido.confianca_minima,
        "contexto_usado": bool(pedido.contexto.strip()),
        "modelo": "convaiinnovations/laya",
        "checkpoint": "multilingual",
        "revisao": revisao_laya_declarada(),
        "pontua": False,
    }


# --- Comparacao BERTimbau x Laya ----------------------------------------------
#
# Os NUMEROS da comparacao vem de um laudo gravado pelo notebook 07, que le
# milhares de exemplos rotulados com os dois modelos. A API so serve o arquivo:
# avaliar ao vivo exigiria os dois modelos e o conjunto de teste dentro do
# deploy. A frase ao vivo e outra coisa -- uma fala, as cabecas que ESTIVEREM
# carregadas, o tempo de cada uma -- e nomeia a que falta em vez de omitir.

LIMIAR_IRONIA_COMPARACAO = 0.5


def _laudo_de_comparacao() -> dict | None:
    try:
        # O laudo local (recem-saido do notebook) vence o versionado com o codigo.
        laudo = metricas_de(CAMINHO_COMPARACAO)
        if laudo is None:
            laudo = metricas_de(CAMINHO_COMPARACAO_PUBLICADA)
        if laudo is not None:
            validar_laudo(laudo)
    except ValueError as erro:  # inclui JSON invalido
        raise HTTPException(
            status_code=500, detail=f"laudo de comparação ilegível: {erro}"
        ) from erro
    return laudo


@router.get("/modelo/comparacao")
def comparacao() -> dict:
    """O laudo do notebook 07, ou `laudo: null` enquanto ele nao foi gerado."""
    return {"laudo": _laudo_de_comparacao()}


@router.get("/modelo/comparacao/relatorio")
def relatorio_comparacao() -> PlainTextResponse:
    """O mesmo laudo por extenso, em Markdown, montado no servidor."""
    laudo = _laudo_de_comparacao()
    if laudo is None:
        raise HTTPException(
            status_code=404,
            detail="não há laudo de comparação: nem modelos/comparacao_modelos.json "
                   "nem o laudo versionado em fraus/dados/",
        )
    return PlainTextResponse(
        relatorio_markdown(laudo),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="comparacao-modelos.md"'},
    )


def _leitura_ironia(prob_ironia: float, ms: float, executor: str) -> dict:
    return {
        "disponivel": True,
        "prob_ironia": prob_ironia,
        "classe": "ironico" if prob_ironia >= LIMIAR_IRONIA_COMPARACAO else "nao-ironico",
        "ms": ms,
        "executor": executor,
    }


def _leitura_emocao(probabilidades: list[float], ms: float, executor: str) -> dict:
    return {
        "disponivel": True,
        "probabilidades": dict(zip(NOMES_EMOCOES, probabilidades)),
        "classe": NOMES_EMOCOES[max(range(len(probabilidades)), key=probabilidades.__getitem__)],
        "ms": ms,
        "executor": executor,
    }


def _indisponivel(motivo: str) -> dict:
    return {"disponivel": False, "motivo": motivo}


def _cronometrar(classificador, texto: str) -> tuple[list[float], float]:
    inicio = time.perf_counter()
    probabilidades = classificador.prever_mensagens([texto])[0]
    return [float(p) for p in probabilidades], (time.perf_counter() - inicio) * 1000


@router.post("/modelo/comparacao/simular")
def simular_comparacao(
    pedido: PedidoSimulacao, ctx: Contexto = Depends(obter_contexto)
) -> dict:
    """Uma fala lida pelas cabecas carregadas, lado a lado -- nao persiste nem pontua."""
    texto = pedido.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="texto vazio")
    if len(texto) > TETO_TEXTO_SIMULACAO:
        raise HTTPException(
            status_code=400,
            detail=f"texto acima do limite de {TETO_TEXTO_SIMULACAO} caracteres",
        )
    ler_cabecas = getattr(ctx.motor, "ler_cabecas", None)
    if ler_cabecas is None:
        raise HTTPException(
            status_code=409,
            detail="o motor em uso é de demonstração e não expõe as cabeças de leitura",
        )
    cabecas = ler_cabecas(texto)
    executor = backend_declarado()
    executor_ironia = backend_ironia_declarado()
    artefato_laya = (CAMINHO_ONNX_LAYA / "laya.onnx").is_file()

    em_uso = cabecas["ironia"]
    if executor_ironia == "padrao":
        ironia_bertimbau = _leitura_ironia(em_uso["prob_ironia"], em_uso["ms"], executor)
        if artefato_laya:
            try:
                from fraus.sinais.ironia_laya import obter_classificador_ironia_laya_onnx

                probabilidades, ms = _cronometrar(obter_classificador_ironia_laya_onnx(), texto)
                ironia_laya = _leitura_ironia(probabilidades[1], ms, "laya-onnx")
            except Exception as erro:  # leitura lateral: a falha dela nao derruba a outra
                ironia_laya = _indisponivel(f"o Laya não carregou: {erro}")
        else:
            ironia_laya = _indisponivel(
                "o artefato do Laya não está neste servidor "
                f"({CAMINHO_ONNX_LAYA.name}/laya.onnx)"
            )
    else:
        # A cabeca de ironia em uso JA e o Laya; o BERTimbau de ironia nao sobe.
        ironia_laya = _leitura_ironia(em_uso["prob_ironia"], em_uso["ms"], executor_ironia)
        ironia_bertimbau = _indisponivel(
            f"FRAUS_IRONIA_BACKEND={executor_ironia}: a cabeça BERTimbau de ironia "
            "não é carregada neste servidor"
        )

    emocao_bertimbau = _leitura_emocao(
        cabecas["emocao"]["probabilidades"], cabecas["emocao"]["ms"], executor
    )
    if artefato_laya:
        try:
            from fraus.sinais.emocao_laya import obter_classificador_emocao_laya_onnx

            probabilidades, ms = _cronometrar(obter_classificador_emocao_laya_onnx(), texto)
            emocao_laya = _leitura_emocao(probabilidades, ms, "laya-onnx")
        except Exception as erro:
            emocao_laya = _indisponivel(str(erro))
    else:
        emocao_laya = _indisponivel(
            "o Laya treinado para emoção não está neste servidor "
            f"({CAMINHO_ONNX_LAYA.name}/laya.onnx)"
        )

    return {
        "texto": texto,
        "tarefas": {
            "ironia": {"bertimbau": ironia_bertimbau, "laya": ironia_laya},
            "emocao": {"bertimbau": emocao_bertimbau, "laya": emocao_laya},
        },
        "limiar_ironia": LIMIAR_IRONIA_COMPARACAO,
        "passada_unica": cabecas["passada_unica"],
        "pontua": False,
    }
