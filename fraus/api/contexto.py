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
from fraus.sinais.curadoria import Curadoria


@dataclass(frozen=True)
class Contexto:
    banco: Banco
    motor: Motor
    raiz: Path
    chave_mestra: str | None
    # Autenticacao de USUARIO (spec 2026-08-31): o segredo que assina o JWT de
    # sessao e o codigo de convite que permite um cadastro nascer `dev`. Os
    # dois moram no ambiente, nunca no banco -- a mesma regra da mestra e do
    # segredo de webhook. `None` = a instalacao nao ofereceu essa porta.
    jwt_segredo: str | None = None
    codigo_dev: str | None = None
    # Codigo exigido para CRIAR CONTA -- diferente do `codigo_dev`, que decide
    # com qual papel a conta nasce. `None` deixa o cadastro aberto, que e o
    # comportamento de sempre e o certo para uso local. Ver
    # `fraus.api.rotas.auth.papel_do_cadastro` para o porque de ele existir.
    codigo_convite: str | None = None

    def autenticacao_ligada(self) -> bool:
        """Se alguma mestra existe -- do ambiente ou gravada pela tela."""
        return self.origem_da_mestra() is not None

    def origem_da_mestra(self) -> str | None:
        """De onde vem a mestra vigente: "ambiente", "banco" ou None.

        Duas procedencias porque resolvem problemas diferentes: a variavel e o
        caminho de quem opera por ambiente (e a saida de quem perdeu a chave
        gerada pela tela), e o banco e o que faz a autenticacao ligada por
        botao SOBREVIVER a reiniciar o processo.

        O ambiente vence -- e a fonte declarada do deploy. Ler as duas A CADA
        requisicao e o que permite ligar a autenticacao sem derrubar o
        servidor: nao existe copia do estado envelhecendo em memoria.
        """
        if self.chave_mestra is not None:
            return "ambiente"
        if self.banco.hash_da_chave_mestra() is not None:
            return "banco"
        return None

    def faixas_vigentes(self) -> dict:
        """Faixa de NPS da configuracao vigente, lida a cada requisicao.

        Ler por requisicao (em vez de guardar num atributo) e o que garante
        que `/indicadores` e `/conversas` NUNCA discordem: nao existe copia da
        faixa envelhecendo em memoria depois de um PUT.
        """
        return faixas_de(carregar_configuracao(self.banco))

    def curadoria_vigente(self) -> Curadoria:
        """O que o analista ensinou ao lexico, lido A CADA requisicao.

        Irma de `faixas_vigentes`, pelo mesmo motivo escrito la: nao existe
        copia do estado envelhecendo em memoria depois de uma escrita. O `Motor`
        e construido uma vez no boot e continua sem saber da curadoria -- quem a
        passa e a rota, no momento de pontuar.
        """
        return self.banco.carregar_curadoria()

    def regua_vigente(self) -> str | None:
        """Assinatura do motor servindo (`Motor.regua`); `None` para duble."""
        regua = getattr(self.motor, "regua", None)
        return regua() if callable(regua) else None

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
