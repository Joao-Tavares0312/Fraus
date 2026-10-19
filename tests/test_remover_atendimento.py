"""Remover um atendimento gravado -- so conta `dev`, e fica na auditoria.

Existe por causa de 19/10/2026: o banco de producao guardava um atendimento
datado de 19/04/2243 (o id do chat lido como horario, antes do conserto de
02/10) e duplicatas de envios de teste. Sem rota de remocao, a unica saida era
SQL direto no Supabase.
"""

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from tests.test_auth import CODIGO_DEV, MESTRA, SEGREDO_JWT, MotorFalso
from tests.test_chave_de_fonte_por_dev import _token
from tests.test_ingestao_tars import _turnos
from tests.test_vazao_de_ingestao import _fonte_com_chave


def _gravar(tmp_path):
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    aberto = TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path))
    chave = _fonte_com_chave(aberto, nome="TARS")
    resposta = aberto.post("/ingestao", headers={"Authorization": f"Bearer {chave}"},
                           json={"id": "x", "mensagens": _turnos(1)})
    return banco, resposta.json()["id"]


def test_sem_autenticacao_remove_e_some_da_lista(tmp_path):
    banco, ident = _gravar(tmp_path)
    cliente = TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path))
    assert cliente.delete(f"/conversas/{ident}").status_code == 204
    assert cliente.get(f"/conversas/{ident}").status_code == 404
    assert banco.todas() == []


def test_inexistente_e_404(tmp_path):
    banco, _ = _gravar(tmp_path)
    cliente = TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path))
    assert cliente.delete("/conversas/nao-existe").status_code == 404


def test_so_dev_remove(tmp_path):
    banco, ident = _gravar(tmp_path)
    cliente = TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
                                   chave_mestra=MESTRA, jwt_segredo=SEGREDO_JWT, codigo_dev=CODIGO_DEV))
    usuario = _token(cliente, "ana@empresa.com", dev=False)
    assert cliente.delete(f"/conversas/{ident}", headers=usuario).status_code == 403
    dev = _token(cliente, "dev@empresa.com", dev=True)
    assert cliente.delete(f"/conversas/{ident}", headers=dev).status_code == 204
    assert banco.todas() == []
