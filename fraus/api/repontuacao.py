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

LIMITES DECLARADOS:

- O estado mora na MEMORIA do processo. Reiniciar a API no meio perde o
  progresso, nao o que ja foi gravado: cada conversa e salva com a
  `lexico_versao` com que foi pontuada, e o aviso de regua misturada volta a
  contar as que faltaram. Repontuar de novo termina o servico.
- Um processo, um trabalho. Com varios workers do uvicorn cada um teria o seu
  -- e o projeto recomenda um worker so (cada um carregaria os tres modelos).
"""

import threading
from datetime import datetime, timezone


class RepontuacaoEmAndamento(RuntimeError):
    """Ja ha uma rodando: duas gravariam o mesmo banco com duas curadorias."""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repontuacao:
    def __init__(self) -> None:
        self._trava = threading.Lock()
        self._estado: dict | None = None

    def estado(self) -> dict | None:
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
            if self._estado is not None and self._estado["estado"] == "rodando":
                raise RepontuacaoEmAndamento()
            curadoria = ctx.curadoria_vigente()
            faixas = ctx.faixas_vigentes()
            # Ordem por id: deterministica nos dois dialetos (sem ORDER BY o
            # Postgres nao promete ordem), e quem retoma sabe onde parou.
            conversas = sorted((c for c, _ in ctx.banco.todas()), key=lambda c: c.id)
            self._estado = {
                "estado": "rodando",
                "total": len(conversas),
                "feitas": 0,
                "erro": None,
                "iniciado_em": _agora(),
                "concluido_em": None,
            }
            inicial = dict(self._estado)

        threading.Thread(
            target=self._rodar,
            args=(ctx, conversas, curadoria, faixas),
            name="fraus-repontuacao",
            daemon=True,
        ).start()
        return inicial

    def _rodar(self, ctx, conversas, curadoria, faixas) -> None:
        try:
            for conversa in conversas:
                score = ctx.motor.pontuar_conversa(conversa, curadoria)
                ctx.banco.salvar(
                    conversa,
                    score,
                    ctx.categoria_de(score, faixas),
                    lexico_versao=curadoria.versao,
                )
                with self._trava:
                    self._estado["feitas"] += 1
            final, erro = "concluido", None
        except Exception as falha:  # noqa: BLE001 - o estado precisa registrar QUALQUER queda
            final, erro = "falhou", f"{type(falha).__name__}: {falha}"
        with self._trava:
            self._estado.update(estado=final, erro=erro, concluido_em=_agora())
