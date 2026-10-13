"""Custo da leitura de transcricao em prosa (auditoria de 13/10/2026).

As tres rotas de /analisar e /conversas/importar leem .txt/.docx/.pdf por
aqui, com qualquer credencial valida. Os dois defeitos eram quadraticos.
"""

import time
from datetime import datetime, timezone

from fraus.ingest import transcricao

INICIO = datetime(2026, 9, 15, 10, tzinfo=timezone.utc)


def test_linha_com_muito_espaco_antes_do_texto_e_linear():
    """`^\\s*` disputava os espacos com o autor e com o `\\s*` antes do `:`:
    8 mil espacos e um `x` levavam ~7,7 s."""
    inicio = time.perf_counter()
    transcricao.ler(" " * 8000 + "x", INICIO)
    assert time.perf_counter() - inicio < 0.5


def test_pii_que_atravessa_a_quebra_de_linha_continua_censurada():
    lida = transcricao.ler("Cliente: meu cpf e\n529.982.247-25 e o email\nfulano@exemplo.com", INICIO)
    texto = lida.mensagens[0].texto
    assert "529.982.247-25" not in texto
    assert "fulano@exemplo.com" not in texto
