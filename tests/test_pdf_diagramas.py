"""O PDF nao pode trocar silenciosamente um diagrama por codigo ou erro."""
import logging

import pytest

bs4 = pytest.importorskip('bs4')
from pdf_event_hook import pre_pdf_render


@pytest.mark.parametrize('conteudo', [
    '<code>flowchart TD; A --&gt; B</code>',
    '<svg><g class="error-icon"/></svg>',
    '<img src="https://example.test/mermaid.svg">',
])
def test_pdf_recusa_diagrama_que_nao_foi_renderizado(conteudo):
    soup = bs4.BeautifulSoup(
        f'<html><body><pre class="fraus-pdf-mermaid">{conteudo}</pre></body></html>',
        'html.parser',
    )
    with pytest.raises(RuntimeError, match='Mermaid do PDF nao renderizado'):
        pre_pdf_render(soup, logging.getLogger('teste'))
