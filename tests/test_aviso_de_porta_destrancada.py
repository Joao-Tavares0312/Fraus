"""O aviso de subida para a combinacao que PARECE fechada e nao esta.

O BURACO JA ESTA FECHADO -- por `FRAUS_CODIGO_CONVITE`, e
`tests/test_cadastro_por_convite.py` prova que ele fecha. O defeito que ESTES
testes cobrem e outro, e e de comunicacao: a defesa e OPT-IN E SILENCIOSA.

Quem define `FRAUS_CHAVE_MESTRA` acredita ter trancado a API -- e um
`GET /conversas` anonimo confirma, com 401. Mas se `FRAUS_JWT_SEGREDO` tambem
esta definido e o convite nao, a sequencia
`POST /auth/registrar` -> `POST /auth/entrar` -> `GET /conversas` com o JWT
le tudo, porque `acesso_autorizado` aceita qualquer sessao valida do mesmo
jeito que aceita a mestra. Deixar de ser anonimo e de graca. Reproduzido em
02/09/2026 e de novo em 08/09/2026.

Os unicos avisos de boot que existiam eram sobre AUSENCIA de autenticacao. A
configuracao perigosa nao e ausencia -- ela tem as duas portas ligadas -- entao
passava calada. Este modulo existe para que ela nao passe mais.

POR QUE AVISO E NAO RECUSA DE SUBIR: a invariante 7 recusa subir por modelo
ausente porque servir predicao errada e pior que ficar fora do ar. Aqui e o
contrario -- cadastro aberto e o comportamento CERTO para uso local, que e o
uso declarado do projeto. Recusar subir puniria o caso comum para avisar o
raro. O que faltava era a frase, nao a tranca.
"""

from fraus.api.main import aviso_de_porta_destrancada

MESTRA = "frm_uma-mestra-qualquer"
JWT = "segredo-de-teste-bem-longo"
CONVITE = "codigo-de-convite"


# ---- a combinacao perigosa ----------------------------------------------


def test_mestra_mais_login_sem_convite_avisa():
    """O caso em si. Este e o teste que impede a regressao."""
    aviso = aviso_de_porta_destrancada(
        mestra_ligada=True, jwt_segredo=JWT, codigo_convite=None
    )
    assert aviso is not None


def test_o_aviso_nomeia_a_variavel_que_conserta():
    """Aviso que descreve o problema e nao diz o que fazer transfere a
    investigacao para quem opera. A defesa tem nome; ele tem de aparecer."""
    aviso = aviso_de_porta_destrancada(
        mestra_ligada=True, jwt_segredo=JWT, codigo_convite=None
    )
    assert "FRAUS_CODIGO_CONVITE" in aviso


def test_o_aviso_descreve_a_sequencia_do_ataque():
    """Sem a sequencia o aviso parece zelo excessivo, e quem opera o ignora."""
    aviso = aviso_de_porta_destrancada(
        mestra_ligada=True, jwt_segredo=JWT, codigo_convite=None
    )
    assert "/auth/registrar" in aviso


# ---- o que NAO pode virar barulho ---------------------------------------


def test_com_o_convite_definido_nao_avisa():
    """A porta esta trancada. Avisar aqui treinaria quem opera a ignorar o
    aviso -- que e como um alarme que toca sempre deixa de ser alarme."""
    assert aviso_de_porta_destrancada(
        mestra_ligada=True, jwt_segredo=JWT, codigo_convite=CONVITE
    ) is None


def test_sem_login_de_usuario_nao_avisa():
    """Sem `FRAUS_JWT_SEGREDO` nao existe sessao para virar credencial: o
    cadastro pode ate criar conta, mas nao ha por onde entrar. A mestra sozinha
    de fato fecha."""
    assert aviso_de_porta_destrancada(
        mestra_ligada=True, jwt_segredo=None, codigo_convite=None
    ) is None


def test_sem_mestra_nao_avisa_de_novo():
    """Instalacao sem mestra ja recebe o aviso de "API sem autenticacao". Um
    segundo aviso sobre a mesma coisa dilui os dois."""
    assert aviso_de_porta_destrancada(
        mestra_ligada=False, jwt_segredo=JWT, codigo_convite=None
    ) is None


def test_convite_vazio_e_o_mesmo_que_ausente():
    """A string vazia exigiria digitar nada para cadastrar -- pareceria fechado
    e estaria aberto, que e a pior das combinacoes. `criar_app` ja trata vazio
    como ausente; o aviso tem de concordar com ele."""
    assert aviso_de_porta_destrancada(
        mestra_ligada=True, jwt_segredo=JWT, codigo_convite=""
    ) is not None
