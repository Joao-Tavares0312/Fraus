"""O miolo das duas rotas de ENTRADA: montar, pontuar, derivar e gravar.

Existe para que `POST /ingestao` (chave de fonte) e
`POST /integracoes/webhook/{fonte_id}` (assinatura) nao mantenham duas copias
da mesma regra. Duas copias divergem, e a invariante 3 do projeto -- veredito
derivado no servidor, nunca aceito do cliente -- nasceu exatamente de uma
divergencia dessas. A que envelhece e sempre a que ninguem olha.
"""

from fastapi import HTTPException
from pydantic import ValidationError

from fraus.api.contexto import Contexto
from fraus.api.esquemas import PedidoIngestao
from fraus.indicadores import nota_0_10
from fraus.modelos import Conversa
from fraus.seguranca.pii import censurar_pii


def resumo_validacao(erro: ValidationError) -> str:
    """Mensagem de erro SEM o valor de entrada -- so o caminho e o tipo.

    `str(ValidationError)` embute o `input_value` recebido na mensagem (e para
    JSON malformado, ate o corpo cru inteiro). Essa mensagem acaba gravada em
    `entregas_webhook.motivo` e devolvida no `detail` do 400 -- as duas saidas
    persistem ou expoem PII de cliente real. `erro.errors()` traz o mesmo
    diagnostico campo a campo; usamos so `loc` (onde) e `type` (o que), e
    descartamos `input`/`msg`/`ctx` de proposito, porque QUALQUER um deles pode
    carregar o valor recebido.

    A GARANTIA TEM UMA CONDICAO, e ela nao e obvia: `loc` e seguro porque hoje
    todo caminho de `PedidoIngestao` e um nome de campo declarado no codigo ou
    um indice de lista. Isso deixaria de valer em dois casos --

    - se `PedidoIngestao` ganhar um campo `dict` de chaves livres (metadados,
      por exemplo): a CHAVE vinda do input entra no `loc`, e chave de dicionario
      e valor de entrada como qualquer outro;
    - se algum modelo passar a `extra="forbid"`: o erro `extra_forbidden` traz
      no `loc` o nome do campo que o cliente inventou.

    Hoje nao existe nenhum dos dois. Quem acrescentar um dos dois precisa
    filtrar `loc` aqui, ou esta funcao deixa de ser a defesa de PII que a rota
    anonima do webhook confia que ela e.
    """
    partes = []
    for item in erro.errors():
        caminho = ".".join(str(p) for p in item["loc"])
        # Sem `loc` -- o caso de `json_invalid`, em que o erro e do corpo
        # inteiro e nao de um campo. Interpolar o caminho vazio produzia
        # "contrato:  (json_invalid)", com o espaco duplo, e essa string vai
        # inteira para a coluna `motivo` e para a tela de Entregas.
        partes.append(f"{caminho} ({item['type']})" if caminho else f"({item['type']})")
    return "corpo nao bate o contrato: " + ", ".join(partes)


def registrar_conversa(ctx: Contexto, pedido: PedidoIngestao, fonte: dict) -> dict:
    """Grava o atendimento e devolve o veredito DERIVADO.

    O CANAL e o da fonte cadastrada, nao o que veio no corpo: quem manda o dado
    nao escolhe em que canal ele e contabilizado, do mesmo jeito que nao escolhe
    a propria nota.
    """
    # PII morre AQUI, no ponto de entrada compartilhado pelas duas rotas --
    # nao mais adiante. Depois deste ponto nao existe texto cru no processo:
    # nem para o banco, nem para os sete sinais, nem para a tela. Este e o
    # mesmo motivo pelo qual o miolo de derivacao mora neste modulo: uma
    # segunda copia da regra em `/ingestao` e no webhook divergiria, e a que
    # envelhece e sempre a que ninguem olha.
    mensagens_limpas = [
        mensagem.model_copy(update={"texto": censurar_pii(mensagem.texto)})
        for mensagem in pedido.mensagens
    ]
    try:
        conversa = Conversa(
            id=pedido.id,
            canal=fonte["canal"],
            iniciada_em=pedido.mensagens[0].enviada_em,
            encerrada_em=pedido.encerrada_em,
            escalou_para_humano=pedido.escalou_para_humano,
            mensagens=sorted(mensagens_limpas, key=lambda m: m.enviada_em),
        )
    except ValidationError as erro:
        raise HTTPException(status_code=400, detail=resumo_validacao(erro)) from erro

    # UMA leitura de curadoria, e e a MESMA que grava a versao: reler abriria
    # janela para pontuar com um lexico e marcar com a versao de outro.
    curadoria = ctx.curadoria_vigente()
    score = ctx.motor.pontuar_conversa(conversa, curadoria)
    # UMA leitura de faixa por requisicao: derivar a categoria duas vezes abria
    # janela para a gravacao e a resposta lerem configuracoes diferentes, e as
    # duas precisam contar a mesma historia.
    categoria = ctx.categoria_de(score, ctx.faixas_vigentes())
    ctx.banco.salvar(
        conversa, score, categoria,
        lexico_versao=curadoria.versao, regua=ctx.regua_vigente(),
    )
    return {
        "id": conversa.id,
        "canal": conversa.canal,
        "score": score,
        "nota": nota_0_10(score) if score is not None else None,
        "categoria": categoria,
        "fonte": fonte["nome"],
    }
