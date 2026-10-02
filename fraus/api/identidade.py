"""O id de uma conversa cujo arquivo nao traz id, e o dia de uma que nao traz dia.

Integracao e CSV canonico trazem o id do sistema de origem, e regravar o mesmo
id e o contrato (reimportar corrige, nao duplica). Dois casos nao tem esse id:

- **arquivo sem coluna de conversa**, e toda transcricao em prosa. O leitor
  devolve um nome de enfeite ("conversa", ou o nome do arquivo), e gravar com
  ele faz o segundo arquivo apagar o primeiro. `Extracao.id_do_arquivo` marca
  o caso; a importacao da pasta usa `id_pelo_caminho` e o upload da tela de
  Analisar usa `id_pelo_conteudo`.
- **transcricao que traz a hora e nao o dia** (`Extracao.tem_data` falso). O
  dia e o do envio. Ele fica fora do id, senao o mesmo arquivo reenviado
  amanha vira outra conversa; e o reenvio conserva o dia ja gravado
  (`no_dia_ja_gravado`), senao a serie de um dia passado muda sozinha.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import PurePath

from fraus.fuso import dia_do_produto
from fraus.modelos import Conversa

PREFIXO_ARQUIVO = "arquivo:"
PREFIXO_ANALISE = "analise:"


def _resumo(valor: object, tamanho: int) -> str:
    texto = json.dumps(valor, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(texto.encode()).hexdigest()[:tamanho]


def id_pelo_caminho(caminho_relativo: PurePath) -> str:
    """Um arquivo da pasta de importacao e UMA conversa: o caminho e a identidade.

    O nome entra legivel para quem le a tabela; o resumo do caminho inteiro
    separa `maio/atendimento.csv` de `junho/atendimento.csv`.
    """
    caminho = caminho_relativo.as_posix()
    return f"{PREFIXO_ARQUIVO}{caminho_relativo.stem[:40]}:{_resumo(caminho, 12)}"


def id_pelo_conteudo(conversa: Conversa, *, tem_data: bool = True) -> str:
    """Reenvio identico recebe o mesmo id.

    Com data, a formula e a de sempre -- mudar faria toda analise ja gravada
    deixar de deduplicar. Sem data, saem do resumo o dia (que e o do envio) e
    o id (que e o nome do arquivo no disco de quem enviou); ficam a hora da
    primeira fala e o intervalo de cada uma ate ela.
    """
    dados = conversa.model_dump(mode="json")
    if not tem_data:
        primeira = conversa.mensagens[0].enviada_em

        def relativo(instante: datetime | None) -> float | None:
            return None if instante is None else (instante - primeira).total_seconds()

        del dados["id"]
        dados["iniciada_em"] = primeira.time().isoformat()
        dados["encerrada_em"] = relativo(conversa.encerrada_em)
        for mensagem, crua in zip(conversa.mensagens, dados["mensagens"]):
            crua["enviada_em"] = relativo(mensagem.enviada_em)
    return PREFIXO_ANALISE + _resumo(dados, 32)


def no_dia_ja_gravado(conversa: Conversa, gravada: Conversa | None) -> Conversa:
    """A conversa sem dia, levada para o dia em que ja foi gravada."""
    if gravada is None:
        return conversa
    dias = (dia_do_produto(gravada.iniciada_em) - dia_do_produto(conversa.iniciada_em)).days
    if dias == 0:
        return conversa
    salto = timedelta(days=dias)
    return conversa.model_copy(update={
        "iniciada_em": conversa.iniciada_em + salto,
        "encerrada_em": None if conversa.encerrada_em is None else conversa.encerrada_em + salto,
        "mensagens": [
            m.model_copy(update={"enviada_em": m.enviada_em + salto}) for m in conversa.mensagens
        ],
    })
