"""Smoke de inferencia real e persistencia; nunca usa o destino de producao.

uv run python scripts/validar_operacao_real.py
uv run python scripts/validar_operacao_real.py --servir (porta 8001, banco temporario)
--postgres aceita somente o banco local fraus_validacao usado nos testes.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["FRAUS_BACKEND"] = "onnx"

from fastapi.testclient import TestClient
from fraus.api.main import construir_motor_padrao, criar_app
from fraus.db import Banco


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--postgres")
    parser.add_argument("--servir", action="store_true")
    parser.add_argument("--porta", type=int, default=8017)
    args = parser.parse_args()
    if args.postgres:
        url = urlparse(args.postgres)
        if url.hostname not in ("localhost", "127.0.0.1") or url.path != "/fraus_validacao":
            raise ValueError("use somente o PostgreSQL local de validacao")
    with TemporaryDirectory(prefix="fraus-operacao-real-") as pasta:
        banco = Banco(args.postgres or Path(pasta) / "validacao.db")
        banco.migrar()
        motor = construir_motor_padrao()
        app = criar_app(banco, motor, raiz_importacao=Path(pasta), jwt_segredo="segredo-local-de-validacao-com-32-caracteres", codigo_dev="validacao-dev")
        cli = TestClient(app)
        cabecalho = "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
        dados = cabecalho + "".join(f"real-{i},chat,cliente,cobranca duplicada preciso estorno,2026-09-{15+i:02}T10:00:00+00:00,true\nreal-{i},chat,humano,vou verificar,2026-09-{15+i:02}T10:05:00+00:00,true\n" for i in range(3))
        r = cli.post("/analisar/registrar", files={"arquivo": ("validacao.csv", dados, "text/csv")})
        assert r.status_code == 200, r.text
        ids = r.json()["gravacao"]["ids"]
        total = len(banco.todas())
        repeticao = cli.post("/analisar/registrar", files={"arquivo": ("validacao.csv", dados, "text/csv")})
        assert repeticao.status_code == 200 and repeticao.json()["gravacao"]["ids"] == ids and len(banco.todas()) == total
        indicadores = cli.get("/indicadores?de=2026-09-15&ate=2026-09-17").json()
        assert indicadores["total_conversas"] >= 3 and all(banco.buscar(i)[1] is not None for i in ids)
        grafo = cli.get("/grafo?de=2026-09-15&ate=2026-09-17").json()
        assert all(any(n["id"] == "conversa:" + i for n in grafo["nos"]) for i in ids)
        assert cli.get("/operacao/replay/" + ids[0]).status_code == 200
        assert cli.post("/operacao/laboratorio/cenario", json={"conversa_id": ids[0], "espera_maxima_s": 30}).status_code == 200
        assert cli.get("/operacao/radar").status_code == 200
        cadastro = cli.post("/auth/registrar", json={"nome": "Pessoa de validacao", "email": "validacao@example.test", "senha": "validacao-local-123", "codigo_dev": "validacao-dev"})
        if cadastro.status_code == 201:
            entrada = cli.post("/auth/entrar", json={"email": "validacao@example.test", "senha": "validacao-local-123"})
            h = {"Authorization": "Bearer " + entrada.json()["token"]}
            cli.post("/operacao/equipes", headers=h, json={"nome": "Equipe de validacao", "canais": ["chat"], "competencias": ["estorno"]})
        print(json.dumps({"motor": "real-onnx", "banco": banco.dialeto, "salvas": len(ids), "reenvio_sem_duplicacao": True, "filtro_indicadores": True, "grafo_atualizado": True, "replay": True, "cenario": True, "radar": True}))
        if args.servir:
            import uvicorn
            uvicorn.run(app, host="127.0.0.1", port=args.porta, access_log=False)
        banco.fechar()


if __name__ == "__main__":
    main()
