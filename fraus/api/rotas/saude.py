"""GET /saude -- a rota que responde antes de qualquer dependencia.

E `/saude/deriva`, o degrau seguinte: "respondeu", "esta medindo" e "esta
medindo DENTRO DA FAIXA EM QUE FOI TREINADO" sao tres afirmacoes diferentes, e
so as duas primeiras eram verificaveis daqui.
"""

from fastapi import APIRouter, Depends, HTTPException

from fraus.api.contexto import Contexto, obter_contexto
from fraus.motor import Motor

router = APIRouter()

# Teto da amostra da rota de deriva. Nao e paranoia de tamanho de resposta: a
# resposta e sempre 39 linhas. Cada conversa da amostra custa uma passagem
# COMPLETA de BERTimbau (satisfacao + emocao), em CPU, dentro da requisicao --
# `n=100000` seria um jeito de derrubar a API por uma rota de diagnostico.
TETO_DA_AMOSTRA = 500
AMOSTRA_PADRAO = 50


@router.get("/saude")
def saude(ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Responde se a API esta de pe E qual motor esta servindo.

    O SEGUNDO CAMPO NASCEU DE UM DEFEITO REAL, em 04/09/2026: a rota dizia so
    `{"status": "ok"}`, o `scripts/api_demo.py` estava no dublê por causa do
    diretorio de onde foi lancado, e o rodape da dashboard escreveu "API no ar"
    durante um dia inteiro enquanto TODO numero da tela era sintetico -- as
    importancias por feature sairam numa progressao 0,2 / 0,25 / 0,3 e passaram
    por peso de regressao logistica.

    "Respondeu" e "esta medindo" sao afirmacoes diferentes, e so a primeira era
    verificavel daqui. Numa ferramenta batizada com o nome do daimon do engano,
    deixar a interface anunciar a segunda sem poder conferi-la e a falha que
    mais custa.

    A DUVIDA CAI PARA `duble`, nunca para `real`: quem decide e ser instancia
    do `Motor` de verdade, e qualquer outra coisa -- dublê da demo, objeto de
    teste, motor de terceiro -- e tratada como possivelmente sintetica. Errar
    para este lado custa uma etiqueta a mais na tela; errar para o outro
    apresenta invencao como medicao.
    """
    return {
        "status": "ok",
        "motor": "real" if isinstance(ctx.motor, Motor) else "duble",
    }


@router.get("/saude/deriva")
def deriva(n: int = AMOSTRA_PADRAO, ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Quais features da amostra recente sairam da faixa de treino do fusor.

    A INVARIANTE 10 VIRANDO ALARME DE RUNTIME. A guarda de vazamento existente
    roda no notebook, sobre o CORPUS -- e o corpus do sinal de tempo nunca
    passou de minutos. Quando aparece uma conversa de tres horas, o z-score do
    `StandardScaler` explode e o relogio assume a nota (medido em 08/09/2026:
    latencia pesando 20x o texto, score em 4,4e-24) sem nada na API reclamar.

    Ela NAO altera predicao nenhuma e nao mexe no `Fusor`. O conserto de
    verdade -- `log1p` ou winsorizacao antes do scaler -- exige RETREINO. Esta
    rota torna o caso visivel enquanto o conserto nao vem, e responde a
    pergunta "e se aparecer um caso fora do treino?" com um endpoint em vez de
    uma promessa.

    Por que da para fazer sem retreinar: o `StandardScaler` treinado ja carrega
    `mean_` e `scale_` por feature dentro do artefato. Ler nao e treinar.

    503 com motor dublê, pela mesma logica da invariante 7: relatorio de
    deriva montado sobre um scaler que nao existe se leria como "nenhuma
    feature fora da faixa", que e a afirmacao mais tranquilizadora possivel e
    sem lastro nenhum.
    """
    if n < 1 or n > TETO_DA_AMOSTRA:
        raise HTTPException(
            400,
            f"n precisa estar entre 1 e {TETO_DA_AMOSTRA}: cada conversa da "
            "amostra custa uma passagem completa de modelo em CPU.",
        )
    if not isinstance(ctx.motor, Motor):
        raise HTTPException(
            503,
            "diagnostico de deriva exige o motor real: o dublê nao tem "
            "distribuicao de treino, e um relatorio vazio dali se leria como "
            "'nenhuma feature fora da faixa'.",
        )

    # As N mais recentes: o que interessa e o que esta chegando AGORA, nao a
    # media historica do banco -- deriva e um fenomeno de borda temporal.
    registros = sorted(
        ctx.banco.todas(), key=lambda par: par[0].iniciada_em, reverse=True
    )[:n]
    conversas = [conversa for conversa, _ in registros]

    resumo = ctx.motor.deriva_da_amostra(conversas, ctx.curadoria_vigente())
    if resumo is None:
        raise HTTPException(503, "o fusor carregado nao tem distribuicao de treino")
    return {"conversas_pedidas": n, **resumo}
