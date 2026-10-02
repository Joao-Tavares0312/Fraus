"""Os defeitos da auditoria de 02/10/2026, um teste por defeito.

Ficam juntos porque nasceram juntos e nenhum deles e de um modulo so: cada um
atravessa uma fronteira (thread x requisicao, escopo x banco, rede x porteiro)
que a suite por modulo nao exercitava. O numero no cabecalho de cada bloco e o
do relatorio da auditoria.
"""

import json
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from fraus import assinatura
from fraus.api.main import criar_app
from fraus.api.rotas.webhook import PREFIXO_WEBHOOK
from fraus.db import VEREDITOS, Banco, _ConexaoPostgres
from fraus.ingest.arquivos import ArquivoIlegivelError, extrair
from fraus.ingest.transcricao import ler
from fraus.modelos import Conversa, Mensagem
from fraus.operacao import PARADAS

# Reusa as fixtures dos vizinhos -- um segundo app para manter em dia e o que
# `tests/test_webhook.py` ja se recusa a criar.
from tests.test_api import CSV, cliente  # noqa: F401
from tests.test_convites_equipe import convidar, registrar
from tests.test_operacao import ambiente  # noqa: F401
from tests.test_webhook import CORPO, SEGREDO, _entregas, _enviar, fonte  # noqa: F401

QUANDO = datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)


def _conversa(id_="c1", canal="chat", falas=1):
    return Conversa(
        id=id_, canal=canal, iniciada_em=QUANDO,
        mensagens=[
            Mensagem(
                autor="cliente", texto=f"meu boleto veio errado {n}",
                enviada_em=QUANDO + timedelta(minutes=n),
            )
            for n in range(falas)
        ],
    )


def _aguardar(cliente, limite_s=10.0):  # noqa: F811
    fim = time.monotonic() + limite_s
    while time.monotonic() < fim:
        estado = cliente.get("/conversas/repontuar").json()
        if estado["estado"] != "rodando":
            return estado
        time.sleep(0.02)
    raise AssertionError("repontuacao nao terminou no prazo")


# --- 1. repontuacao x reenvio concorrente -----------------------------------


def test_reenvio_durante_a_repontuacao_nao_e_revertido(tmp_path):
    """A thread carrega o instantaneo UMA vez. Se a fonte reenvia o atendimento
    com mais mensagens enquanto ela roda, gravar a linha inteira devolveria a
    conversa ao que era -- a fala nova some, sem erro nenhum."""
    entrou, liberar = threading.Event(), threading.Event()

    class MotorComPausa:
        def pontuar_conversa(self, conversa, curadoria=None):
            entrou.set()
            liberar.wait(5)
            return 50.0

    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    banco.salvar(_conversa(falas=2), 20.0, "detrator", lexico_versao=0)
    cliente = TestClient(  # noqa: F811
        criar_app(banco=banco, motor=MotorComPausa(), raiz_importacao=tmp_path)
    )

    assert cliente.post("/conversas/repontuar").status_code == 202
    assert entrou.wait(5)
    # O reenvio, pontuado por quem reenviou com a regua vigente.
    banco.salvar(_conversa(falas=3), 80.0, "promotor", lexico_versao=7, regua="regua-do-reenvio")
    liberar.set()
    assert _aguardar(cliente)["estado"] == "concluido"

    conversa, score, categoria = banco.buscar("c1")
    assert len(conversa.mensagens) == 3
    assert (score, categoria) == (80.0, "promotor")
    assert banco.regua_da_conversa("c1") == (7, "regua-do-reenvio")


def test_repontuacao_normal_continua_atualizando_score_e_regua(tmp_path):
    class MotorComRegua:
        def pontuar_conversa(self, conversa, curadoria=None):
            return 95.0

        def regua(self):
            return "regua-nova"

    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    banco.salvar(_conversa(falas=2), 20.0, "detrator", lexico_versao=0, regua="regua-velha")
    cliente = TestClient(  # noqa: F811
        criar_app(banco=banco, motor=MotorComRegua(), raiz_importacao=tmp_path)
    )
    cliente.post("/lexico/curado", json={"tipo": "palavra", "termo": "x", "peso": -1})

    assert cliente.post("/conversas/repontuar").status_code == 202
    assert _aguardar(cliente)["estado"] == "concluido"

    conversa, score, categoria = banco.buscar("c1")
    assert (score, categoria) == (95.0, "promotor")
    assert banco.regua_da_conversa("c1") == (1, "regua-nova")
    assert conversa == _conversa(falas=2)


def test_repontuacao_alcanca_linha_gravada_antes_de_um_campo_novo(tmp_path):
    """O payload de uma linha antiga NAO e byte a byte o `model_dump_json()` de
    hoje: `feedback_declarado` e `comentario_feedback` entraram no modelo em
    28/09/2026. Comparar com a reserializacao pularia toda linha anterior a
    isso, para sempre -- a repontuacao diria "concluido" e a regua seguiria
    misturada."""
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    banco.salvar(_conversa(), 20.0, "detrator", lexico_versao=0)
    antigo = _conversa().model_dump(mode="json")
    del antigo["feedback_declarado"], antigo["comentario_feedback"]
    with banco._conectar() as conexao:
        conexao.execute(
            "UPDATE conversas SET payload = ? WHERE id = ?", (json.dumps(antigo), "c1")
        )
    (instantaneo, _), = banco.todas()

    assert banco.atualizar_pontuacao(instantaneo, 95.0, "promotor", lexico_versao=3, regua="r") is True
    assert banco.buscar("c1")[1:] == (95.0, "promotor")
    assert banco.regua_da_conversa("c1") == (3, "r")


def test_atualizar_pontuacao_nao_cria_o_que_foi_apagado(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    assert banco.atualizar_pontuacao(_conversa(), 95.0, "promotor") is False
    assert banco.todas() == []


# --- 2. /ingestao com as mensagens fora de ordem ----------------------------


def test_ingestao_fora_de_ordem_comeca_na_mensagem_mais_antiga(cliente):  # noqa: F811
    fonte_id = cliente.post(
        "/integracoes/fontes", json={"nome": "X", "canal": "chat", "tipo": "webhook"}
    ).json()["id"]
    chave = cliente.post(f"/integracoes/fontes/{fonte_id}/chave").json()["chave"]
    resposta = cliente.post(
        "/ingestao",
        headers={"Authorization": f"Bearer {chave}"},
        json={"id": "t1", "mensagens": [
            {"autor": "bot", "texto": "posso ajudar em algo mais?",
             "enviada_em": "2026-09-15T10:05:00+00:00"},
            {"autor": "cliente", "texto": "meu boleto veio errado",
             "enviada_em": "2026-09-15T10:00:00+00:00"},
        ]},
    )
    assert resposta.status_code == 201, resposta.text

    linha = cliente.get("/conversas").json()[0]
    assert datetime.fromisoformat(linha["iniciada_em"]) == QUANDO
    assert linha["duracao_s"] == 300


# --- 3. webhook: assinatura nao ASCII, falha interna ------------------------


def test_confere_recusa_assinatura_nao_ascii_sem_levantar():
    """`hmac.compare_digest` so aceita `str` ASCII: com acento ele levanta
    TypeError, e quem escolhe o cabecalho e um anonimo."""
    assert assinatura.confere("msg_1", "1", b"{}", SEGREDO, "v1,ééé") is False
    boa = assinatura.assinar("msg_1", "1", b"{}", SEGREDO)
    assert assinatura.confere("msg_1", "1", b"{}", SEGREDO, f"v1,ééé {boa}") is True


def test_assinatura_nao_ascii_e_401_e_fica_registrada(cliente, fonte):  # noqa: F811
    sem_estourar = TestClient(cliente.app, raise_server_exceptions=False)
    resposta = sem_estourar.post(
        f"{PREFIXO_WEBHOOK}/{fonte['id']}",
        content=json.dumps(CORPO).encode(),
        # Em bytes: o httpx recusa montar cabecalho `str` fora do ASCII, e na
        # rede o que chega e o byte.
        headers=[
            (b"webhook-id", b"msg_1"),
            (b"webhook-timestamp", str(int(time.time())).encode()),
            (b"webhook-signature", "v1,ééé".encode("latin-1")),
        ],
    )
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "assinatura nao confere"
    (entrega,) = _entregas(cliente, fonte["id"])
    assert entrega["veredito"] == "assinatura"


def test_falha_interna_do_webhook_fica_registrada_e_continua_500(
    cliente, fonte, monkeypatch,  # noqa: F811
):
    """Excecao que nao e `Recusa` saia como 500 sem linha nenhuma: no historico
    da fonte, "nao chegou nada" e "chegou e a API quebrou" eram a mesma tela."""

    def quebrar(*_args, **_kwargs):
        raise RuntimeError("fala do cliente: meu cpf e 123")

    sem_estourar = TestClient(cliente.app, raise_server_exceptions=False)
    # Contexto proprio: `monkeypatch.undo()` desfaria tambem o segredo que a
    # fixture `fonte` pos no ambiente.
    with monkeypatch.context() as remendo:
        remendo.setattr("fraus.api.rotas.webhook.registrar_conversa", quebrar)
        assert _enviar(sem_estourar, fonte["id"]).status_code == 500

    (entrega,) = _entregas(cliente, fonte["id"])
    assert entrega["veredito"] == "erro"
    assert entrega["veredito"] in VEREDITOS
    assert "RuntimeError" in entrega["motivo"]
    # So o TIPO: o texto de uma excecao pode carregar o que veio no corpo.
    assert "cpf" not in entrega["motivo"]
    # Falha interna nao queima o `webhook-id`: a plataforma retenta e entra.
    assert _enviar(cliente, fonte["id"]).status_code == 201


# --- 5. arquivo plausivel nao pode virar 500 --------------------------------


@pytest.mark.parametrize("hora", ["24:00", "75:30", "10:61", "10:00:75"])
def test_marcador_fora_de_faixa_nao_e_horario(hora):
    """`24:00` e `75:30` (minuto:segundo de gravacao) casam com a forma de um
    horario e nao sao um. Sem horario reconhecido nao ha latencia -- e nao se
    inventa hora para ter."""
    transcricao = ler(
        f"{hora} Cliente: meu pedido nao chegou\n{hora} Atendente: vou verificar", QUANDO
    )
    assert [m.autor for m in transcricao.mensagens] == ["cliente", "humano"]
    assert transcricao.tem_tempo is False


def test_marcador_invalido_no_meio_nao_derruba_os_horarios_validos():
    transcricao = ler(
        "10:00 Cliente: meu pedido nao chegou\n"
        "99:99 Atendente: vou verificar\n"
        "10:03 Cliente: obrigado, resolveu",
        QUANDO,
    )
    assert transcricao.tem_tempo is True
    assert len(transcricao.mensagens) == 3
    assert transcricao.mensagens[2].enviada_em == QUANDO.replace(minute=3)


CSV_COM_ASPAS_ABERTAS = (
    "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
    'c1,chat,cliente,"aspas que nao fecham ' + "texto longo " * 12000
    + ",2026-08-13T10:00:00+00:00,false\n"
)


def test_csv_com_aspas_sem_fechar_e_arquivo_ilegivel_e_diz_por_que():
    with pytest.raises(ArquivoIlegivelError) as erro:
        extrair("c.csv", CSV_COM_ASPAS_ABERTAS.encode())
    assert "aspas" in str(erro.value)


def test_analisar_responde_400_para_arquivo_plausivel_e_quebrado(cliente):  # noqa: F811
    sem_estourar = TestClient(cliente.app, raise_server_exceptions=False)
    resposta = sem_estourar.post("/analisar", json={"csv": CSV_COM_ASPAS_ABERTAS, "nome": "c.csv"})
    assert resposta.status_code == 400
    assert "aspas" in resposta.json()["detail"]

    resposta = sem_estourar.post("/analisar", json={
        "csv": "24:00 Cliente: meu pedido nao chegou\n24:05 Atendente: vou verificar",
        "nome": "conversa.txt",
    })
    assert resposta.status_code == 200, resposta.text


# --- 6. contar_defasadas com escopo -----------------------------------------


def test_defasadas_com_escopo_seguem_a_mesma_regra_da_base(ambiente):  # noqa: F811
    """Linha sem `lexico_versao` vale ZERO (ver `Banco.contar_defasadas`). A
    versao com escopo comparava `None != 0` e abria a tela de quem tem escopo
    com todo o banco em alarme, enquanto o dev via zero no mesmo banco."""
    cli, banco, h, u = ambiente
    cli.put(
        f"/operacao/acesso/{u['usuario']}", headers=h["dev"],
        json={"canais": ["chat", "email"], "exportar_minutos": 10},
    )
    campos = ("pontuadas_com_lexico_antigo", "total_no_banco", "pontuadas_com_regua_antiga")
    do_dev = cli.get("/indicadores", headers=h["dev"]).json()
    do_usuario = cli.get("/indicadores", headers=h["usuario"]).json()
    assert {c: do_usuario[c] for c in campos} == {c: do_dev[c] for c in campos}
    assert do_usuario["pontuadas_com_lexico_antigo"] == 0


def test_defasadas_com_escopo_contam_so_os_canais_e_numa_consulta(tmp_path):
    from fraus.api.escopo import BancoComEscopo

    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    banco.salvar(_conversa("a", "chat"), 50.0, "neutro", lexico_versao=0, regua="r")
    banco.salvar(_conversa("b", "chat"), 50.0, "neutro", lexico_versao=None, regua=None)
    banco.salvar(_conversa("c", "email"), 50.0, "neutro", lexico_versao=0, regua="r")

    assert banco.contar_defasadas("r") == (1, 3)
    assert banco.contar_defasadas("r", canais=["email"]) == (0, 1)
    assert banco.contar_defasadas(canais=[]) == (0, 0)

    conexoes = []
    original = banco._conectar
    banco._conectar = lambda: conexoes.append(1) or original()
    assert BancoComEscopo(banco, ["chat"]).contar_defasadas("r") == (1, 2)
    # A versao do lexico e a contagem: duas, e nao uma por conversa.
    assert len(conexoes) == 2


# --- 7. criar equipe recalcula escopo ---------------------------------------


def test_criar_equipe_ja_com_o_membro_concede_os_canais_na_hora(ambiente):  # noqa: F811
    """So `alterar_documento` recalculava o escopo de quem entrou por convite:
    criada a equipe com a pessoa dentro, ela ficava sem os canais ate alguem
    editar QUALQUER equipe."""
    cli, banco, h, u = ambiente
    suporte = cli.post(
        "/operacao/equipes", headers=h["dev"], json={"nome": "Suporte", "canais": ["chat"]}
    ).json()
    convite = convidar(cli, h["dev"], suporte["id"])
    nova, hn = registrar(cli, convite["token"])
    assert cli.post(f"/operacao/convites/{convite['token']}/aceitar", headers=hn).status_code == 200
    assert banco.documento("permissao", str(nova["id"]))["canais"] == ["chat"]

    resposta = cli.post(
        "/operacao/equipes", headers=h["dev"],
        json={"nome": "Email", "canais": ["email"], "membros": [nova["id"]]},
    )
    assert resposta.status_code == 200, resposta.text
    assert banco.documento("permissao", str(nova["id"]))["canais"] == ["chat", "email"]
    assert {c["id"] for c in cli.get("/conversas", headers=hn).json()} == {"c1", "c2"}


# --- 8. id externo com barra ------------------------------------------------


def test_id_com_barra_tem_detalhe_e_atribuicao(cliente):  # noqa: F811
    fonte_id = cliente.post(
        "/integracoes/fontes", json={"nome": "X", "canal": "chat", "tipo": "webhook"}
    ).json()["id"]
    chave = cliente.post(f"/integracoes/fontes/{fonte_id}/chave").json()["chave"]
    conversa_id = cliente.post(
        "/ingestao",
        headers={"Authorization": f"Bearer {chave}"},
        json={"id": "2026/000123", "mensagens": [
            {"autor": "cliente", "texto": "boleto errado demais",
             "enviada_em": "2026-09-15T11:00:00+00:00"},
        ]},
    ).json()["id"]
    assert conversa_id == f"fonte:{fonte_id}:2026/000123"

    for forma in (quote(conversa_id, safe=""), conversa_id):
        detalhe = cliente.get(f"/conversas/{forma}")
        assert detalhe.status_code == 200, detalhe.text
        assert detalhe.json()["id"] == conversa_id
        atribuicao = cliente.get(f"/conversas/{forma}/atribuicao")
        assert atribuicao.status_code == 200, atribuicao.text
        assert atribuicao.json()["conversa_id"] == conversa_id


def test_rota_de_id_com_barra_nao_engole_as_irmas(cliente, tmp_path):  # noqa: F811
    # `/conversas/repontuar` continua sendo o progresso, nao um id.
    progresso = cliente.get("/conversas/repontuar")
    assert progresso.status_code == 404
    assert "repontuacao" in progresso.json()["detail"]

    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    assert cliente.post("/conversas/importar/previa", json={"caminho": str(caminho)}).status_code == 200
    assert cliente.post("/conversas/importar", json={"caminho": str(caminho)}).json()["importadas"] == 1

    # O sufixo `/atribuicao` continua sendo a atribuicao, e nao parte do id.
    assert cliente.get("/conversas/c1").json()["id"] == "c1"
    assert "importancias" in cliente.get("/conversas/c1/atribuicao").json()
    assert cliente.get("/conversas/nao/existe").status_code == 404
    assert cliente.get("/conversas/nao/existe/atribuicao").status_code == 404


# --- 9. a conexao volta ao pool mesmo quando o commit falha -----------------


class _PoolFalso:
    def __init__(self):
        self.fora = 0

    @contextmanager
    def connection(self):
        self.fora += 1
        try:
            yield _ConexaoQueCaiu()
        finally:
            self.fora -= 1


class _ConexaoQueCaiu:
    def commit(self):
        raise RuntimeError("the connection is closed (commit)")

    def rollback(self):
        raise RuntimeError("the connection is closed (rollback)")

    def execute(self, *_args):
        raise ValueError("consulta falhou")


@pytest.mark.parametrize("falha_na_consulta", [False, True])
def test_conexao_postgres_volta_ao_pool_quando_commit_ou_rollback_falha(falha_na_consulta):
    """Sem `finally`, a conexao que caiu no meio ficava emprestada para sempre
    -- e o teto do pool serverless e DOIS."""
    pool = _PoolFalso()
    contexto = pool.connection()
    conexao = _ConexaoPostgres(contexto.__enter__())
    conexao._contexto = contexto
    assert pool.fora == 1

    with pytest.raises(RuntimeError, match="connection is closed"):
        with conexao:
            if falha_na_consulta:
                conexao._conexao.execute("SELECT 1")
    assert pool.fora == 0


# --- 10. stop words do radar ------------------------------------------------


def test_palavra_vazia_acentuada_nao_vira_termo_de_tema():
    from sklearn.feature_extraction.text import TfidfVectorizer

    vetor = TfidfVectorizer(stop_words=PARADAS, ngram_range=(1, 1))
    vetor.fit(["não já você vocês está às nao ja voce esta boleto"])
    assert sorted(vetor.get_feature_names_out()) == ["boleto"]
