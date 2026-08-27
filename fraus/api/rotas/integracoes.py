"""/integracoes -- por onde o atendimento entra, e o cadastro de cada porta.

Uma FONTE e o registro de uma origem de conversa: nome, canal e tipo. A chave
dela (`frs_...`) e a credencial de `POST /ingestao`, sai em claro uma unica
vez e e privilegio da mestra emitir ou revogar.

Tambem mora aqui o que a tela de Integracoes precisa saber para nao manter
copia propria: os TIPOS que a ingestao sabe tratar, os ARQUIVOS disponiveis na
raiz de importacao e o HISTORICO do que ja entrou.
"""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from fraus import assinatura, credencial
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import TIPOS_DE_FONTE, PedidoAjusteFonte, PedidoFonte
from fraus.api.seguranca import exigir_mestra

router = APIRouter()


def fonte_publica(fonte: dict) -> dict:
    """Fonte como ela pode sair pela rede: o segredo nao acompanha.

    So o NOME da variavel de ambiente e o fato de ela estar definida. A
    verificacao e feita na LEITURA, nao no cadastro: a variavel pode aparecer
    ou sumir do ambiente depois, e responder pelo que era verdade no cadastro
    seria mentir sobre o estado atual.
    """
    variavel = fonte["variavel_segredo"]
    return {**fonte, "configurada": bool(variavel and os.environ.get(variavel))}


@router.get("/integracoes/fontes")
def listar_fontes(ctx: Contexto = Depends(obter_contexto)) -> list[dict]:
    """Fontes cadastradas, cada uma com `configurada` derivado do ambiente.

    `configurada` responde apenas SE a variavel de ambiente existe. O valor
    do segredo nunca sai daqui -- nem parcial, nem mascarado: mascara e
    vazamento de tamanho e de prefixo por um caminho mais lento.
    """
    return [fonte_publica(fonte) for fonte in ctx.banco.listar_fontes()]


@router.post("/integracoes/fontes", status_code=201)
def criar_fonte(
    pedido: PedidoFonte, ctx: Contexto = Depends(obter_contexto)
) -> dict:
    nome = pedido.nome.strip()
    if not nome:
        raise HTTPException(status_code=400, detail="nome da fonte vazio")
    canal = pedido.canal.strip()
    if not canal:
        raise HTTPException(status_code=400, detail="canal da fonte vazio")
    if pedido.tipo not in TIPOS_DE_FONTE:
        raise HTTPException(
            status_code=400,
            detail=f"tipo de fonte desconhecido: {pedido.tipo} "
                   f"(esperado: {', '.join(TIPOS_DE_FONTE)})",
        )
    fonte = ctx.banco.criar_fonte(
        nome=nome,
        canal=canal,
        tipo=pedido.tipo,
        variavel_segredo=(pedido.variavel_segredo or "").strip() or None,
        criada_em=datetime.now(timezone.utc).isoformat(),
    )
    return fonte_publica(fonte)


@router.patch("/integracoes/fontes/{fonte_id}")
def ajustar_fonte(
    fonte_id: int,
    pedido: PedidoAjusteFonte,
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    if ctx.banco.buscar_fonte(fonte_id) is None:
        raise HTTPException(status_code=404, detail="fonte nao encontrada")
    nome = None
    if pedido.nome is not None:
        nome = pedido.nome.strip()
        if not nome:
            raise HTTPException(status_code=400, detail="nome da fonte vazio")
    return fonte_publica(ctx.banco.atualizar_fonte(fonte_id, nome=nome, ativa=pedido.ativa))


@router.delete("/integracoes/fontes/{fonte_id}", status_code=204)
def apagar_fonte(
    fonte_id: int, ctx: Contexto = Depends(obter_contexto)
) -> None:
    """Remove o CADASTRO da fonte. Nenhuma conversa e apagada junto.

    Conversa que ja entrou e dado de atendimento medido; a fonte e so o
    registro de por onde ele entrou. Apagar a origem nao pode reescrever o
    historico -- e por isso que nao ha exclusao em cascata aqui.
    """
    if not ctx.banco.apagar_fonte(fonte_id):
        raise HTTPException(status_code=404, detail="fonte nao encontrada")


@router.post("/integracoes/fontes/{fonte_id}/chave", status_code=201)
def gerar_chave(
    fonte_id: int,
    authorization: str | None = Header(default=None),
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Gera a chave de API da fonte e a devolve EM CLARO uma unica vez.

    Nao ha rota para reler a chave depois, e isso e a feature: o banco
    guarda so o hash, entao um `fraus.db` vazado num backup nao leva
    credencial junto. Perder a chave custa gerar outra.

    Gerar substitui a anterior. Duas chaves validas ao mesmo tempo pareceria
    rotacao sem risco, mas a antiga seguiria aceita sem ninguem saber quem
    ainda a usa.
    """
    exigir_mestra(ctx, authorization)
    if ctx.banco.buscar_fonte(fonte_id) is None:
        raise HTTPException(status_code=404, detail="fonte nao encontrada")

    chave, chave_hash = credencial.gerar(fonte_id)
    fonte = ctx.banco.gravar_chave(
        fonte_id,
        chave_hash=chave_hash,
        dica=credencial.dica(chave),
        criada_em=datetime.now(timezone.utc).isoformat(),
    )
    return {
        "fonte": fonte_publica(fonte),
        # Unica vez que este campo existe em qualquer resposta da API.
        "chave": chave,
        "aviso": (
            "Guarde agora: esta chave nao pode ser lida de novo. "
            "O servidor guarda apenas o hash dela."
        ),
    }


@router.delete("/integracoes/fontes/{fonte_id}/chave", status_code=204)
def revogar_chave(
    fonte_id: int,
    authorization: str | None = Header(default=None),
    ctx: Contexto = Depends(obter_contexto),
) -> None:
    """Invalida a chave da fonte. A fonte e as conversas dela continuam."""
    exigir_mestra(ctx, authorization)
    if ctx.banco.buscar_fonte(fonte_id) is None:
        raise HTTPException(status_code=404, detail="fonte nao encontrada")
    ctx.banco.revogar_chave(fonte_id)


@router.post("/integracoes/fontes/{fonte_id}/segredo", status_code=201)
def gerar_segredo(
    fonte_id: int,
    authorization: str | None = Header(default=None),
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Gera o segredo de assinatura do webhook e o devolve EM CLARO uma vez.

    E A UNICA ROTA DESTE PROJETO QUE NAO GRAVA A CREDENCIAL QUE EMITE -- nem o
    hash. E de proposito: HMAC exige o segredo em claro no servidor toda vez
    que uma assinatura e conferida, e guardar valor recuperavel no SQLite
    desfaria a propriedade que faz um backup vazado nao levar credencial
    junto.

    O valor mora na variavel de ambiente que a fonte nomeia. O fluxo do
    operador tem tres passos e a tela mostra os tres: gerar, por na variavel de
    ambiente da maquina da API, entregar a copia a plataforma.

    Privilegio da mestra, como as demais rotas de credencial: uma chave que
    emite outra chave nao seria um posto menor.
    """
    exigir_mestra(ctx, authorization)
    fonte = ctx.banco.buscar_fonte(fonte_id)
    if fonte is None:
        raise HTTPException(status_code=404, detail="fonte nao encontrada")

    variavel = fonte["variavel_segredo"]
    return {
        "segredo": assinatura.gerar_segredo(),
        # O NOME da variavel onde ele deve ser posto. `None` quando a fonte nao
        # nomeia nenhuma -- a tela precisa saber a diferenca para pedir o
        # cadastro em vez de mandar o operador adivinhar onde por o valor.
        "variavel": variavel,
        "aviso": (
            "Guarde agora: este segredo nao e gravado em lugar nenhum pelo Fraus. "
            + (
                f"Defina {variavel} com este valor no ambiente da API e entregue "
                "a mesma copia a plataforma."
                if variavel
                else "Cadastre antes o nome da variavel de ambiente desta fonte."
            )
        ),
    }


@router.get("/integracoes/fontes/{fonte_id}/entregas")
def listar_entregas_da_fonte(
    fonte_id: int, ctx: Contexto = Depends(obter_contexto)
) -> list[dict]:
    """Historico de entregas de webhook da fonte, mais recente primeiro.

    O corpo da requisicao nunca aparece aqui -- e PII de cliente real, e
    depurar se resolve com veredito e motivo, nunca com o payload guardado.
    """
    if ctx.banco.buscar_fonte(fonte_id) is None:
        raise HTTPException(status_code=404, detail="fonte nao encontrada")
    return ctx.banco.listar_entregas(fonte_id)


@router.get("/integracoes/tipos")
def tipos_de_fonte() -> list[dict]:
    """Os tipos que a ingestao sabe tratar HOJE.

    Existe para a interface parar de manter a propria copia da lista. Ela
    mantinha, e a copia so ficaria errada no dia em que um tipo novo
    entrasse aqui: o formulario seguiria oferecendo dois, e o terceiro
    existiria na API sem existir na tela -- divergencia que nao levanta
    erro nenhum, so some da vista.
    """
    return [
        {
            "valor": "csv",
            "rotulo": "CSV",
            "ajuda": "arquivo importado por POST /conversas/importar",
        },
        {
            "valor": "webhook",
            "rotulo": "Webhook",
            "ajuda": (
                "a plataforma chama POST /integracoes/webhook/{id} com o evento "
                "assinado"
            ),
        },
    ]


@router.get("/integracoes/arquivos")
def arquivos_importaveis(ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Os CSV disponiveis na raiz de importacao.

    A rota de importacao aceita um caminho RELATIVO a raiz e recusa
    qualquer escape. Sem esta listagem, quem opera precisava adivinhar o
    nome do arquivo ou sair da interface para olhar a pasta -- e digitar
    nome de arquivo de memoria e como um caminho errado vira "arquivo nao
    encontrado" sem ninguem entender por que.

    Devolve NOME e tamanho, nunca caminho absoluto: o cliente nao precisa
    saber onde a pasta fica no disco, e a resposta nao vaza a arvore da
    maquina. A busca desce em subpastas porque a raiz pode ser organizada
    por mes ou canal.
    """
    raiz_resolvida = ctx.raiz.resolve()
    if not raiz_resolvida.is_dir():
        return {"raiz": raiz_resolvida.name, "arquivos": []}

    arquivos = []
    for caminho in sorted(raiz_resolvida.rglob("*.csv")):
        if not caminho.is_file():
            continue
        arquivos.append(
            {
                "caminho": caminho.relative_to(raiz_resolvida).as_posix(),
                "bytes": caminho.stat().st_size,
            }
        )
    return {"raiz": raiz_resolvida.name, "arquivos": arquivos}


@router.get("/integracoes/importacoes")
def listar_importacoes(ctx: Contexto = Depends(obter_contexto)) -> list[dict]:
    """Historico de importacao, mais recente primeiro.

    Registra so o que a ingestao chegou a processar: arquivo recusado na
    porta (caminho fora da raiz, coluna estrutural ausente) nao virou
    importacao nenhuma, e listar como tal seria contar uma tentativa como
    evento de dado.
    """
    return ctx.banco.listar_importacoes()
