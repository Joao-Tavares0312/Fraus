"""O JWT nao e a ultima palavra sobre quem esta entrando.

O BURACO QUE ISTO FECHA. `sessao_do_jwt` decidia so por assinatura e `exp`, e
nunca consultava `usuarios.ativo`. So `/auth/eu` lia o banco. O resultado,
reproduzido em 02/09/2026 depois de `UPDATE usuarios SET ativo = 0`:

    /auth/eu    -> 401
    /conversas  -> 200

A tela dizia "sessao invalida" e quem opera ACREDITAVA ter cortado o acesso,
enquanto a API servia os dados por ate 12 horas -- a validade do token. O mesmo
valia para o `papel`: ele vinha do payload, entao rebaixar `dev` -> `usuario` so
surtia efeito na expiracao.

O CUSTO E UMA LEITURA POR REQUISICAO, e ela e a mesma que `faixas_vigentes()` ja
paga em toda requisicao. Guardar privilegio dentro de um token que vive 12 horas
so e barato enquanto ninguem precisa revogar nada.

DESATIVAR NAO E O UNICO CAMINHO: a conta pode ser APAGADA. Token de usuario que
nao existe mais tambem tem de morrer, e isso e o mesmo `None` -- por isso o
teste do usuario inexistente esta aqui e nao no arquivo de auth.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from fraus import token_acesso
from fraus.api.main import criar_app
from fraus.db import Banco

SEGREDO_JWT = "segredo-jwt-de-teste-bem-longo"
MESTRA = "mestra-de-teste-com-entropia-suficiente"
SENHA = "senha-longa-o-bastante"


class MotorFalso:
    def pontuar_conversa(self, conversa, curadoria=None):
        return 50.0

    def importancias(self):
        return None


@pytest.fixture
def banco(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    return banco


@pytest.fixture
def cliente(banco, tmp_path):
    """Com mestra definida: e o modo em que a API EXIGE credencial, que e onde
    a sessao de fato governa o acesso."""
    return TestClient(
        criar_app(
            banco=banco,
            motor=MotorFalso(),
            raiz_importacao=tmp_path,
            chave_mestra=MESTRA,
            jwt_segredo=SEGREDO_JWT,
            codigo_dev="codigo-de-dev",
        )
    )


def entrar(cliente, email="ana@empresa.com", codigo=None) -> str:
    corpo = {"nome": "Ana", "email": email, "senha": SENHA}
    if codigo is not None:
        corpo["codigo_dev"] = codigo
    assert cliente.post("/auth/registrar", json=corpo).status_code == 201
    resposta = cliente.post("/auth/entrar", json={"email": email, "senha": SENHA})
    assert resposta.status_code == 200
    return resposta.json()["token"]


def com(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# Estes helpers escrevem SQL cru de proposito: nao existe rota de
# administracao de usuario nesta API, entao desativar uma conta e exatamente
# isto -- um UPDATE no banco. Foi assim que a auditoria de 02/09/2026
# reproduziu o buraco, e o teste imita a operacao real em vez de inventar um
# metodo de producao que nenhuma rota chamaria.
def _executar(banco: Banco, sql: str, parametros: tuple) -> None:
    with banco._conectar() as conexao:
        conexao.execute(sql, parametros)


def desativar(banco: Banco, email: str) -> None:
    _executar(banco, "UPDATE usuarios SET ativo = 0 WHERE lower(email) = lower(?)", (email,))


# --- conta desativada -------------------------------------------------------


def test_conta_desativada_perde_o_acesso_aos_dados(cliente, banco):
    """O buraco em si. Este e o teste que impede a regressao."""
    token = entrar(cliente)
    assert cliente.get("/conversas", headers=com(token)).status_code == 200

    desativar(banco, "ana@empresa.com")

    assert cliente.get("/conversas", headers=com(token)).status_code == 401


def test_a_recusa_concorda_com_o_que_a_tela_ja_dizia(cliente, banco):
    """`/auth/eu` ja respondia 401 -- era o RESTO da API que discordava dele.
    As duas respostas tem de contar a mesma historia."""
    token = entrar(cliente)
    desativar(banco, "ana@empresa.com")

    assert cliente.get("/auth/eu", headers=com(token)).status_code == 401
    assert cliente.get("/conversas", headers=com(token)).status_code == 401


def test_conta_apagada_tambem_perde_o_acesso(cliente, banco):
    token = entrar(cliente)
    _executar(banco, "DELETE FROM usuarios WHERE lower(email) = lower(?)", ("ana@empresa.com",))

    assert cliente.get("/conversas", headers=com(token)).status_code == 401


# --- papel vem do banco, nao do token ---------------------------------------


def test_rebaixar_dev_vale_na_hora_e_nao_na_expiracao(cliente, banco):
    """O `papel` viajava DENTRO do token. Rebaixar no banco nao mudava nada por
    ate 12 horas -- e a rota administrativa continuava aberta."""
    token = entrar(cliente, email="dev@empresa.com", codigo="codigo-de-dev")
    assert cliente.get("/integracoes/fontes", headers=com(token)).status_code == 200

    _executar(banco, "UPDATE usuarios SET papel = ? WHERE lower(email) = lower(?)",
              ("usuario", "dev@empresa.com"))

    resposta = cliente.get("/integracoes/fontes", headers=com(token))
    assert resposta.status_code == 403
    assert "papel dev" in resposta.json()["detail"]


def test_promover_a_dev_tambem_vale_na_hora(cliente, banco):
    """A simetria importa: se o banco manda, ele manda nos dois sentidos.
    Sem isto, quem acabou de ser promovido teria que sair e entrar de novo."""
    token = entrar(cliente)
    assert cliente.get("/integracoes/fontes", headers=com(token)).status_code == 403

    _executar(banco, "UPDATE usuarios SET papel = ? WHERE lower(email) = lower(?)",
              ("dev", "ana@empresa.com"))

    assert cliente.get("/integracoes/fontes", headers=com(token)).status_code == 200


# --- o que NAO pode mudar ---------------------------------------------------


def test_conta_ativa_continua_entrando(cliente):
    token = entrar(cliente)
    assert cliente.get("/conversas", headers=com(token)).status_code == 200
    assert cliente.get("/auth/eu", headers=com(token)).status_code == 200


def test_a_mestra_nao_passa_pelo_banco_de_usuarios(cliente):
    """A mestra nao e usuario nenhum. Se a conferencia da sessao passasse a
    exigir registro, a credencial do deploy morreria junto."""
    assert cliente.get("/conversas", headers=com(MESTRA)).status_code == 200


def test_token_de_outro_segredo_continua_recusado(cliente, banco):
    """Regressao boba e possivel: carregar o usuario ANTES de conferir a
    assinatura faria qualquer token nomeando um id valido passar."""
    forjado = token_acesso.emitir(
        usuario_id=1,
        papel="dev",
        segredo="outro-segredo-completamente-diferente",
        agora=datetime.now(timezone.utc),
    )
    assert cliente.get("/conversas", headers=com(forjado)).status_code == 401
