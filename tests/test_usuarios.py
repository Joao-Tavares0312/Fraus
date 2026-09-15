"""Usuarios da dashboard: senha com scrypt e a tabela que os guarda.

Usuario e IDENTIDADE (quem esta olhando a tela), nao credencial tecnica --
as chaves `fra_`/`frs_` autenticam processos e fontes, e continuam existindo.
Senha tem pouca entropia, entao aqui o hash e scrypt (custo de memoria contra
forca bruta), nao o SHA-256 puro do credencial.py -- la o segredo e sorteado,
aqui e escolhido por gente.
"""


import pytest

from fraus import usuarios
from fraus.db import Banco, ErroDeIntegridade


def _banco(tmp_path) -> Banco:
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return banco


def _criar(banco: Banco, email: str = "ana@empresa.com", papel: str = "usuario") -> dict:
    return banco.criar_usuario(
        nome="Ana",
        email=email,
        senha_hash=usuarios.gerar_hash("segredo-da-ana"),
        papel=papel,
        criado_em="2026-08-31T10:00:00+00:00",
    )


# --- o hash -----------------------------------------------------------------


def test_hash_nao_contem_a_senha_e_declara_o_formato():
    guardado = usuarios.gerar_hash("hunter2")
    assert "hunter2" not in guardado
    assert guardado.startswith("scrypt$")


def test_o_salt_muda_a_cada_chamada():
    # Dois usuarios com a MESMA senha nao podem ter o mesmo hash: hash igual
    # contaria a quem le o banco que as senhas coincidem.
    assert usuarios.gerar_hash("igual") != usuarios.gerar_hash("igual")


def test_confere_aceita_a_senha_certa_e_recusa_a_errada():
    guardado = usuarios.gerar_hash("correta")
    assert usuarios.confere("correta", guardado) is True
    assert usuarios.confere("errada", guardado) is False


@pytest.mark.parametrize("guardado", [None, "", "lixo", "scrypt$so-uma-parte", "md5$a$b"])
def test_confere_recusa_guardado_ausente_ou_fora_do_formato(guardado):
    # Usuario sem hash ou com registro corrompido NUNCA autoriza -- e a recusa
    # nao pode levantar excecao, porque ela roda no caminho do login.
    assert usuarios.confere("qualquer", guardado) is False


# --- a tabela ---------------------------------------------------------------


def test_criar_usuario_devolve_a_ficha_sem_o_hash(tmp_path):
    banco = _banco(tmp_path)
    criado = _criar(banco)
    assert criado["email"] == "ana@empresa.com"
    assert criado["papel"] == "usuario"
    assert criado["ativo"] is True
    assert "senha_hash" not in criado


def test_buscar_por_email_ignora_caixa_e_nao_expoe_o_hash(tmp_path):
    # E-mail e identificador que gente digita: Ana@Empresa.com e ana@empresa.com
    # sao a mesma pessoa, e tratar como duas criaria duas contas irmas.
    banco = _banco(tmp_path)
    _criar(banco)
    achado = banco.buscar_usuario_por_email("ANA@empresa.COM")
    assert achado is not None
    assert achado["nome"] == "Ana"
    assert "senha_hash" not in achado
    assert banco.buscar_usuario_por_email("ninguem@empresa.com") is None


def test_email_duplicado_e_recusado_pelo_banco_mesmo_com_caixa_diferente(tmp_path):
    # A unicidade mora no banco, nao na rota: duas rotas (ou uma corrida)
    # jamais criam a segunda conta, e a borda HTTP traduz o erro em 409.
    banco = _banco(tmp_path)
    _criar(banco)
    with pytest.raises(ErroDeIntegridade):
        _criar(banco, email="Ana@Empresa.com")


def test_papel_fora_do_vocabulario_e_recusado_pelo_banco(tmp_path):
    # `CHECK` no esquema, pelo mesmo motivo do id=1 da chave_mestra: garantia
    # do banco, nao regra que a aplicacao precisa lembrar.
    banco = _banco(tmp_path)
    with pytest.raises(ErroDeIntegridade):
        _criar(banco, papel="root")


def test_o_hash_so_sai_pelo_caminho_explicito(tmp_path):
    banco = _banco(tmp_path)
    criado = _criar(banco)
    guardado = banco.hash_da_senha(criado["id"])
    assert usuarios.confere("segredo-da-ana", guardado) is True
    assert banco.hash_da_senha(criado["id"] + 99) is None


def test_buscar_usuario_por_id(tmp_path):
    banco = _banco(tmp_path)
    criado = _criar(banco)
    achado = banco.buscar_usuario(criado["id"])
    assert achado is not None
    assert achado["email"] == "ana@empresa.com"
    assert "senha_hash" not in achado
    assert banco.buscar_usuario(criado["id"] + 99) is None
