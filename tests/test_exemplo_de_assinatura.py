"""O exemplo de assinatura da tela de Integracoes EXECUTA e a API aceita.

`ContratoDoWebhook.tsx` mostra um trecho de Python que assina uma entrega. Ele
mora em TypeScript, do outro lado da fronteira de linguagem, e nenhum teste
de TS roda Python: o exemplo poderia divergir de `fraus.assinatura` (um
`.decode()` a mais, o ponto do `{id}.{timestamp}.` esquecido) e continuar na
tela ensinando a gerar 401. Mesmo molde de
`test_a_vitrine_anuncia_o_numero_real_de_features`: le o TSX como texto.
"""

import re
from pathlib import Path

from fraus import assinatura

CAMINHO = Path(__file__).resolve().parents[1] / "dashboard/components/integracoes/ContratoDoWebhook.tsx"


def _trecho() -> str:
    fonte = CAMINHO.read_text(encoding="utf-8")
    achado = re.search(r"const EXEMPLO_PYTHON = String\.raw`\n(.*?)`;", fonte, re.S)
    assert achado, "o exemplo de Python sumiu do ContratoDoWebhook.tsx"
    return achado.group(1)


def test_o_exemplo_de_python_gera_assinatura_que_a_api_confere(monkeypatch):
    segredo = assinatura.gerar_segredo()
    monkeypatch.setenv("FRAUS_SEGREDO_WEBHOOK", segredo)
    enviados = []

    import urllib.request

    def urlopen_falso(pedido, *args, **kwargs):
        enviados.append(pedido)

        class Resposta:
            status = 201

            def __enter__(self):
                return self

            def __exit__(self, *erro):
                return False

            def read(self):
                return b"{}"

        return Resposta()

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_falso)
    codigo = _trecho().replace("{URL}", "http://api.exemplo/integracoes/webhook/1")
    exec(compile(codigo, "ContratoDoWebhook.tsx", "exec"), {})

    assert len(enviados) == 1
    pedido = enviados[0]
    cabecalhos = {k.lower(): v for k, v in pedido.header_items()}
    assert assinatura.confere(
        cabecalhos["webhook-id"],
        cabecalhos["webhook-timestamp"],
        pedido.data,
        segredo,
        cabecalhos["webhook-signature"],
    )
