"""GET /saude -- a rota que responde antes de qualquer dependencia."""

from fastapi import APIRouter, Depends

from fraus.api.contexto import Contexto, obter_contexto
from fraus.motor import Motor

router = APIRouter()


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
