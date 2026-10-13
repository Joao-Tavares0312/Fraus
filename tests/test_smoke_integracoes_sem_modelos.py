"""O smoke de integracoes sem os modelos diz que faltam modelos e sai.

Auditoria de 13/10/2026: com os pesos ausentes, o script aceitava
`/saude` com `motor: real` e `estado_motor: erro` como "motor real", seguia
para as entregas (500 em todas) e travava: o stdout do uvicorn ia para um
pipe que ninguem lia, e com os tracebacks o buffer enchia e o servidor
parava de responder. A docstring promete o contrario: "sem eles a API nao
sobe, e o script diz isso em vez de testar um motor duble".
"""

import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    (RAIZ / "modelos" / "bertimbau-satisfacao").is_dir(),
    reason="com os modelos presentes o smoke roda de verdade",
)
def test_sem_modelos_o_smoke_sai_com_1_e_nomeia_a_causa():
    processo = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "smoke_integracoes.py"), "--porta", "8029"],
        cwd=RAIZ, capture_output=True, text=True, timeout=120,
    )
    assert processo.returncode == 1
    assert "modelos" in processo.stdout
    assert "entrega assinada" not in processo.stdout
