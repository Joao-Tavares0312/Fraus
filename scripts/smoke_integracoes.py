"""Teste de fumaca das integracoes contra um SERVIDOR DE VERDADE.

A suite cobre `/ingestao` e o webhook com `TestClient`, que roda o app dentro
do processo do pytest. O que ela nao pega e justamente o que so aparece com
uvicorn de pe e a autenticacao LIGADA -- a armadilha 8 do handoff: a rota do
webhook tomando 401 do middleware de chave de acesso antes de olhar a propria
assinatura, com o ambiente de desenvolvimento (API aberta) sem revelar nada.

O script sobe a API real num banco e num arquivo de chaves temporarios, com o
segredo do webhook no ambiente do processo, percorre o caminho que uma
plataforma percorreria e confere cada status. Sai com codigo 1 se qualquer um
divergir. Nao toca no banco nem nas chaves da instalacao.

    uv run python scripts/smoke_integracoes.py            # porta 8019

Exige os modelos treinados em `modelos/` (invariante 7): sem eles a API nao
sobe, e o script diz isso em vez de testar um motor duble.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from fraus import assinatura  # noqa: E402

VARIAVEL = "FRAUS_SEGREDO_SMOKE"

MENSAGENS = [
    {"autor": "cliente", "texto": "Pedido atrasado de novo, que absurdo!!", "enviada_em": "2026-09-14T10:00:00-03:00"},
    {"autor": "bot", "texto": "Sinto muito, vou verificar.", "enviada_em": "2026-09-14T10:00:20-03:00"},
    {"autor": "cliente", "texto": "resolveu, obrigado", "enviada_em": "2026-09-14T10:03:00-03:00"},
]


def chamar(base: str, metodo: str, caminho: str, corpo: bytes | None = None, cabecalhos=None):
    pedido = urllib.request.Request(base + caminho, data=corpo, method=metodo)
    for nome, valor in (cabecalhos or {}).items():
        pedido.add_header(nome, valor)
    if corpo is not None:
        pedido.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(pedido, timeout=60) as resposta:
            texto = resposta.read().decode()
            return resposta.status, json.loads(texto) if texto else None
    except urllib.error.HTTPError as erro:
        texto = erro.read().decode()
        try:
            return erro.code, json.loads(texto)
        except json.JSONDecodeError:
            return erro.code, texto


class Conferencia:
    def __init__(self) -> None:
        self.falhas = 0

    def status(self, descricao: str, obtido: int, esperado: int) -> None:
        ok = obtido == esperado
        self.falhas += not ok
        marca = "ok  " if ok else "FALHA"
        print(f"  {marca} {descricao:<62} {obtido} (esperado {esperado})")

    def verdade(self, descricao: str, condicao: bool) -> None:
        self.falhas += not condicao
        print(f"  {'ok  ' if condicao else 'FALHA'} {descricao}")


def principal() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--porta", type=int, default=8019)
    args = parser.parse_args()
    base = f"http://127.0.0.1:{args.porta}"

    temporario = Path(tempfile.mkdtemp(prefix="fraus-smoke-"))
    segredo = assinatura.gerar_segredo()
    ambiente = {
        **os.environ,
        "FRAUS_CAMINHO_BANCO": str(temporario / "smoke.db"),
        "FRAUS_CAMINHO_CHAVES": str(temporario / "chaves.txt"),
        VARIAVEL: segredo,
    }
    print(f"subindo a API real em {base} (banco temporario em {temporario})...")
    servidor = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "fraus.api.main:app", "--port", str(args.porta)],
        cwd=RAIZ, env=ambiente, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        for _ in range(180):
            if servidor.poll() is not None:
                print(servidor.stdout.read()[-2000:])
                print("a API nao subiu -- confira se os tres modelos estao em modelos/")
                return 1
            try:
                _, saude = chamar(base, "GET", "/saude")
                break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(1)
        else:
            print("a API nao respondeu /saude em 3 minutos")
            return 1

        c = Conferencia()
        c.verdade(f"/saude declara motor real ({saude})", saude.get("motor") == "real")

        chaves = dict(
            linha.split("=", 1)
            for linha in (temporario / "chaves.txt").read_text().splitlines()
            if "=" in linha and not linha.startswith("#")
        )
        mestra = {"Authorization": f"Bearer {chaves['chave_mestra'].strip()}"}
        acesso = {"Authorization": f"Bearer {chaves['chave_acesso'].strip()}"}

        print("autenticacao ligada:")
        c.status("GET /conversas sem credencial", chamar(base, "GET", "/conversas")[0], 401)

        print("fontes e chave:")
        st, fonte_csv = chamar(base, "POST", "/integracoes/fontes", json.dumps(
            {"nome": "api", "canal": "site", "tipo": "csv"}).encode(), mestra)
        c.status("cria fonte csv", st, 201)
        st, fonte_wh = chamar(base, "POST", "/integracoes/fontes", json.dumps(
            {"nome": "wh", "canal": "whatsapp", "tipo": "webhook", "variavel_segredo": "FRAUS_ERRADA"}).encode(), mestra)
        c.status("cria fonte webhook com a variavel ERRADA", st, 201)
        st, fonte_wh = chamar(base, "PATCH", f"/integracoes/fontes/{fonte_wh['id']}", json.dumps(
            {"variavel_segredo": VARIAVEL}).encode(), mestra)
        c.status("corrige a variavel sem recriar a fonte", st, 200)
        c.verdade("a fonte passa a constar como configurada", fonte_wh.get("configurada") is True)
        st, chave = chamar(base, "POST", f"/integracoes/fontes/{fonte_csv['id']}/chave", None, mestra)
        c.status("emite chave frs_ com a mestra", st, 201)
        c.status("chave fra_ nao emite chave de fonte",
                 chamar(base, "POST", f"/integracoes/fontes/{fonte_csv['id']}/chave", None, acesso)[0], 403)

        print("/ingestao:")
        corpo = json.dumps({"id": "ing-1", "mensagens": MENSAGENS}).encode()
        st, gravada = chamar(base, "POST", "/ingestao", corpo, {"Authorization": f"Bearer {chave['chave']}"})
        c.status("entrega com chave frs_", st, 201)
        c.verdade("score derivado no servidor", isinstance(gravada, dict) and gravada.get("score") is not None)
        c.status("entrega sem chave", chamar(base, "POST", "/ingestao", corpo)[0], 401)

        print("webhook (anonimo por desenho, assinado):")
        corpo = json.dumps({"id": "wh-1", "mensagens": MENSAGENS}).encode()
        webhook_id, carimbo = "msg_smoke_1", str(int(time.time()))
        assinados = {
            "webhook-id": webhook_id,
            "webhook-timestamp": carimbo,
            "webhook-signature": assinatura.assinar(webhook_id, carimbo, corpo, segredo),
        }
        rota = f"/integracoes/webhook/{fonte_wh['id']}"
        c.status("entrega assinada, com a mestra ligada", chamar(base, "POST", rota, corpo, assinados)[0], 201)
        c.status("reentrega do mesmo webhook-id", chamar(base, "POST", rota, corpo, assinados)[0], 200)
        c.status("assinatura invalida", chamar(base, "POST", rota, corpo, {
            **assinados, "webhook-id": "msg_smoke_2", "webhook-signature": "v1,AAAA"})[0], 401)

        print("leitura:")
        st, conversas = chamar(base, "GET", "/conversas", None, acesso)
        c.status("GET /conversas com chave fra_", st, 200)
        ids = {conversa.get("id") for conversa in (conversas or [])}
        c.verdade("as duas entregas aparecem (ing-1 e wh-1)", {"ing-1", "wh-1"} <= ids)
        st, entregas = chamar(base, "GET", f"/integracoes/fontes/{fonte_wh['id']}/entregas", None, mestra)
        vereditos = sorted(e["veredito"] for e in entregas or [])
        c.verdade(f"log de entregas registra os tres vereditos ({vereditos})",
                  {"aceita", "duplicada", "assinatura"} <= set(vereditos))

        print("\n" + ("tudo conferido." if c.falhas == 0 else f"{c.falhas} conferencia(s) falharam."))
        return 0 if c.falhas == 0 else 1
    finally:
        servidor.terminate()
        try:
            servidor.wait(timeout=15)
        except subprocess.TimeoutExpired:
            servidor.kill()
        # O temporario guarda a mestra e a chave de acesso geradas: nao fica.
        shutil.rmtree(temporario, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(principal())
