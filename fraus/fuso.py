"""O fuso em que o produto pensa: o "dia" e a "hora" de uma conversa.

Timestamps chegam com o offset de quem os mandou (invariante 6: sempre com
fuso). O INSTANTE e o que vale para latencia e ordenacao; mas "em que dia foi
este atendimento" e pergunta de calendario, e calendario precisa de um fuso so.

Ate 02/10/2026 cada ponto cortava o dia no offset de origem: a fonte que manda
horario em UTC punha o atendimento das 22h30 no dia seguinte, e o recorte por
periodo, a serie diaria e a tabela discordavam entre si conforme a origem do
dado. Na dashboard o mesmo defeito aparecia como hora tres horas adiantada.

Brasilia, fixo em -03:00, pelo mesmo motivo de `fraus/ingest/totalk.py` e
`fraus/ingest/mapeador.py`: o Brasil nao tem horario de verao desde 2019, entao
nao ha transicao para errar, e depender do banco de fusos do sistema tornaria o
dia dependente da maquina. A dashboard usa o mesmo fuso (`dashboard/lib/fuso.ts`).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

FUSO_DO_PRODUTO = timezone(timedelta(hours=-3))


def no_fuso_do_produto(instante: datetime) -> datetime:
    """O mesmo instante, lido no relogio do produto."""
    return instante.astimezone(FUSO_DO_PRODUTO)


def dia_do_produto(instante: datetime) -> date:
    """O dia de calendario em que o instante caiu, no fuso do produto."""
    return no_fuso_do_produto(instante).date()
