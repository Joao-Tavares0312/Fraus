"""O que as rotas precisam saber, num objeto so.

Ate aqui `banco`, `motor`, `raiz` e `chave_mestra` chegavam nas rotas por
FECHAMENTO LEXICO: toda rota era uma closure dentro de `criar_app`, e era so
isso que impedia elas de morarem em arquivos separados. O `Contexto` troca o
fechamento por injecao -- `Depends(obter_contexto)` -- e cada dominio vira um
modulo de verdade.

O que mora aqui e o que MAIS DE UM dominio usa. O que e de um dominio so fica
no modulo dele: este objeto atravessa a API inteira, e um saco de tudo seria
pior do que a closure que ele veio substituir.
"""

from dataclasses import dataclass
from pathlib import Path

from fastapi import Request

from fraus.api.periodo import no_recorte, recorte_ou_400
from fraus.configuracao import carregar as carregar_configuracao
from fraus.configuracao import faixas_de
from fraus.db import Banco
from fraus.indicadores import categoria_nps
from fraus.motor import Motor


@dataclass(frozen=True)
class Contexto:
    banco: Banco
    motor: Motor
    raiz: Path
    chave_mestra: str | None

    def faixas_vigentes(self) -> dict:
        """Faixa de NPS da configuracao vigente, lida a cada requisicao.

        Ler por requisicao (em vez de guardar num atributo) e o que garante
        que `/indicadores` e `/conversas` NUNCA discordem: nao existe copia da
        faixa envelhecendo em memoria depois de um PUT.
        """
        return faixas_de(carregar_configuracao(self.banco))

    def categoria_de(self, score: float | None, faixas: dict) -> str | None:
        """Categoria DERIVADA NA LEITURA do score gravado e da faixa vigente.

        A coluna `categoria` do banco e o retrato do instante da importacao e
        NAO e lida aqui: mudar a faixa muda a fatia de atendimento ja pontuado,
        e derivar na leitura e o que faz toda rota responder pela mesma faixa
        no mesmo instante -- sem janela de recalculo em massa pela metade. O
        `score`, esse sim resultado do modelo, nunca e recalculado.
        """
        return categoria_nps(score, faixas) if score is not None else None

    def registros_do_recorte(self, de: str | None, ate: str | None) -> list:
        """Conversas do periodo, com a validacao de recorte compartilhada."""
        inicio, fim = recorte_ou_400(de, ate)
        return [
            (conversa, score)
            for conversa, score in self.banco.todas()
            if no_recorte(conversa.iniciada_em, inicio, fim)
        ]


def obter_contexto(request: Request) -> Contexto:
    """A dependencia que toda rota declara. Montada uma vez em `criar_app`."""
    return request.app.state.contexto
