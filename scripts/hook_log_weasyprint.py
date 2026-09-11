"""Faz os erros do WeasyPrint APARECEREM no log do build.

POR QUE ISTO EXISTE. O `mkdocs-to-pdf`, sob `--strict`, CONTA os registros de
nivel ERROR do logger `weasyprint` e derruba o build com a soma
("80 error(s) ... occurred while generating PDF"). Mas essa soma e tudo que
aparece: nenhum dos erros e impresso, e o build morre com um numero e nenhuma
pista.

A causa nao e do plugin, e de encanamento de logging, e ela e invisivel lendo
qualquer um dos arquivos envolvidos sozinho:

  - o MkDocs instala o UNICO StreamHandler dele no logger `mkdocs`, e marca
    `propagate = False` (`mkdocs/__main__.py`, classe `State`);
  - o WeasyPrint loga em `weasyprint`, que traz um `NullHandler` proprio e
    propaga para a raiz -- que nao tem handler nenhum;
  - o `logging.lastResort`, que salvaria o caso imprimindo em stderr, NAO entra:
    ele so age quando NENHUM handler e encontrado, e o `NullHandler` conta como
    encontrado.

Ou seja: os registros existem, sao contados, e caem num buraco.

E por isso que `verbose: true` no plugin nao resolve -- aquela opcao mexe no
NIVEL do logger, nao em quem escuta. Sem um handler, baixar o nivel so produz
mais registros silenciosos.

A correcao e uma linha de encanamento: pendurar um handler no logger
`weasyprint`. Mantemos o nivel como o plugin o deixou, para nao inventar
verbosidade -- o que queremos e exatamente aquilo que ele ja conta.
"""

import logging
import sys

_NOME_HANDLER = "FrausWeasyPrintStreamHandler"


def on_config(config, **kwargs):
    """Pendura um handler no logger do WeasyPrint, uma vez so.

    `on_config` roda a cada build (e o `mkdocs serve` faz muitos), entao a
    insercao e idempotente por nome: sem a guarda, cada rebuild somaria um
    handler e o mesmo erro sairia duplicado, triplicado, e assim por diante.
    """
    logger = logging.getLogger("weasyprint")

    if any(h.name == _NOME_HANDLER for h in logger.handlers):
        return config

    handler = logging.StreamHandler(sys.stderr)
    handler.name = _NOME_HANDLER
    handler.setFormatter(logging.Formatter("WEASYPRINT %(levelname)s: %(message)s"))
    logger.addHandler(handler)

    return config
