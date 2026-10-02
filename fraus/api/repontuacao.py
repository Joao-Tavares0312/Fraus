"""Repontuar o banco em SEGUNDO PLANO, com progresso que a tela le.

POR QUE SAIU DA REQUISICAO. Repontuar roda os tres BERTimbau por conversa.
Sincrona, a rota prendia uma requisicao HTTP pelo banco inteiro: em milhares de
atendimentos o proxy do Next desistia, a tela dizia erro, e o banco ficava
metade numa regua e metade noutra -- sem ninguem saber quantas.

O QUE O DOCSTRING ANTIGO DEFENDIA, E CONTINUA VALENDO: "uma fila que ninguem
observa seria pior que uma espera que se ve". Por isso isto NAO e uma fila:
e UM trabalho por vez, com `total`, `feitas`, `estado` e `erro` lidos por
`GET /conversas/repontuar`, e a tela mostra a barra. Espera que se ve, sem
prender a conexao.

O estado e o lock moram no BANCO. Isso impede duas replicas de iniciarem o
mesmo trabalho e faz o progresso continuar visivel quando o GET cai em outro
processo. Uma execucao sem heartbeat por 15 minutos e considerada abandonada e
pode ser retomada; as linhas ja atualizadas continuam marcadas com a regua nova.
"""

import threading
from datetime import datetime, timedelta, timezone


class RepontuacaoEmAndamento(RuntimeError):
    """Ja ha uma rodando: duas gravariam o mesmo banco com duas curadorias."""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repontuacao:
    NOME_TRABALHO = "repontuacao"

    def __init__(self) -> None:
        self._trava = threading.Lock()
        self._estado: dict | None = None

    def estado(self, banco=None) -> dict | None:
        if banco is not None:
            persistido = banco.estado_do_trabalho(self.NOME_TRABALHO)
            if persistido is not None:
                return persistido
        with self._trava:
            return dict(self._estado) if self._estado is not None else None

    def iniciar(self, ctx) -> dict:
        """Le curadoria, faixa e a lista UMA vez e dispara a thread.

        As tres leituras ficam FORA do laco pelo mesmo motivo de sempre: ler por
        conversa abriria janela para o lote comecar com uma configuracao e
        terminar com outra -- a regua misturada de novo, dentro da rota que
        existe para acabar com ela.
        """
        with self._trava:
            curadoria = ctx.curadoria_vigente()
            faixas = ctx.faixas_vigentes()
            regua = ctx.regua_vigente()
            # Ordem por id: deterministica nos dois dialetos (sem ORDER BY o
            # Postgres nao promete ordem), e quem retoma sabe onde parou.
            conversas = sorted((c for c, _ in ctx.banco.todas()), key=lambda c: c.id)
            iniciado_em = _agora()
            expirado_antes_de = (
                datetime.now(timezone.utc) - timedelta(minutes=15)
            ).isoformat()
            if not ctx.banco.reservar_trabalho(
                self.NOME_TRABALHO,
                len(conversas),
                iniciado_em,
                expirado_antes_de,
            ):
                raise RepontuacaoEmAndamento()
            self._estado = {
                "estado": "rodando",
                "total": len(conversas),
                "feitas": 0,
                "erro": None,
                "iniciado_em": iniciado_em,
                "concluido_em": None,
            }
            inicial = dict(self._estado)

        threading.Thread(
            target=self._rodar,
            args=(ctx, conversas, curadoria, faixas, regua),
            name="fraus-repontuacao",
            daemon=True,
        ).start()
        return inicial

    def _rodar(self, ctx, conversas, curadoria, faixas, regua) -> None:
        try:
            for feitas, conversa in enumerate(conversas, start=1):
                score = ctx.motor.pontuar_conversa(conversa, curadoria)
                # So o veredito, e so se a conversa ainda for a do instantaneo:
                # `salvar` regravaria o payload antigo por cima de um reenvio
                # que chegou enquanto esta thread rodava (02/10/2026). A linha
                # que mudou conta como feita -- quem reenviou ja a pontuou.
                ctx.banco.atualizar_pontuacao(
                    conversa,
                    score,
                    ctx.categoria_de(score, faixas),
                    lexico_versao=curadoria.versao,
                    regua=regua,
                )
                with self._trava:
                    self._estado["feitas"] += 1
                ctx.banco.atualizar_trabalho(
                    self.NOME_TRABALHO, feitas=feitas, agora=_agora()
                )
            final, erro = "concluido", None
        except Exception as falha:  # noqa: BLE001 - o estado precisa registrar QUALQUER queda
            final, erro = "falhou", f"{type(falha).__name__}: {falha}"
        with self._trava:
            self._estado.update(estado=final, erro=erro, concluido_em=_agora())
        ctx.banco.atualizar_trabalho(
            self.NOME_TRABALHO, estado=final, erro=erro, agora=_agora()
        )
