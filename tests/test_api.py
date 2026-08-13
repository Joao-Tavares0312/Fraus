import pytest
from fastapi.testclient import TestClient

from dolos.api.main import criar_app
from dolos.db import Banco
from dolos.fusor import NOMES_FEATURES

CSV = (
    "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
    "c1,csv,cliente,otimo,2026-08-13T10:00:00+00:00,false\n"
    "c1,csv,bot,de nada,2026-08-13T10:00:08+00:00,false\n"
    "c1,csv,cliente,valeu,2026-08-13T10:00:15+00:00,false\n"
)

# Atendimento em que o bot fala sozinho: nenhuma mensagem do cliente.
CSV_SEM_CLIENTE = (
    "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
    "mudo,csv,bot,ola posso ajudar,2026-08-13T11:00:00+00:00,false\n"
    "mudo,csv,bot,continuo por aqui,2026-08-13T11:00:30+00:00,false\n"
)


def _probabilidades_deterministicas(texto: str) -> list[float]:
    """Probabilidades estaveis derivadas do texto -- sem modelo nenhum."""
    peso = (len(texto) % 3) + 1.0
    bruto = [peso, 1.0, 3.0]
    total = sum(bruto)
    return [valor / total for valor in bruto]


class AtribuicaoDuble:
    """Parte de atribuicao comum aos dubles: probabilidade so na fala do cliente."""

    def atribuir_conversa(self, conversa):
        mensagens = []
        for indice, mensagem in enumerate(conversa.mensagens):
            if mensagem.autor == "cliente":
                p = _probabilidades_deterministicas(mensagem.texto)
            else:
                p = [None, None, None]
            mensagens.append(
                {
                    "indice": indice,
                    "autor": mensagem.autor,
                    "texto": mensagem.texto,
                    "prob_insatisfeito": p[0],
                    "prob_neutro": p[1],
                    "prob_satisfeito": p[2],
                }
            )
        contribuicoes = (
            {nome: float((indice % 5) - 2) for indice, nome in enumerate(NOMES_FEATURES)}
            if conversa.tem_sinal_cliente
            else None
        )
        return {
            "mensagens": mensagens,
            "importancias": {nome: 1.0 for nome in NOMES_FEATURES},
            "contribuicoes": contribuicoes,
        }


class MotorFalso(AtribuicaoDuble):
    def pontuar_conversa(self, conversa):
        return 90.0


class MotorRespeitandoSinal(AtribuicaoDuble):
    """Duble que honra o invariante do Motor real: sem fala do cliente, sem score."""

    def pontuar_conversa(self, conversa):
        if not conversa.tem_sinal_cliente:
            return None  # ausencia de dado nao e insatisfacao
        return 90.0


@pytest.fixture
def cliente(tmp_path):
    banco = Banco(tmp_path / "dolos.db")
    banco.migrar()
    return TestClient(
        criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path)
    )


@pytest.fixture
def cliente_com_sinal(tmp_path):
    banco = Banco(tmp_path / "dolos.db")
    banco.migrar()
    return TestClient(
        criar_app(
            banco=banco, motor=MotorRespeitandoSinal(), raiz_importacao=tmp_path
        )
    )


def test_saude_responde_ok(cliente):
    resposta = cliente.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


def test_importar_csv_persiste_e_pontua(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")

    resposta = cliente.post("/conversas/importar", json={"caminho": str(caminho)})
    assert resposta.status_code == 200
    assert resposta.json() == {
        "importadas": 1,
        "rejeitadas": 0,
        "motivos": [],
    }

    listagem = cliente.get("/conversas").json()
    assert len(listagem) == 1
    assert listagem[0]["score"] == 90.0
    assert listagem[0]["categoria"] == "promotor"
    # A nota tambem vem do servidor: a dashboard nunca a recalcula.
    assert listagem[0]["nota"] == 9


def test_categoria_enviada_pelo_cliente_e_ignorada(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post(
        "/conversas/importar",
        json={"caminho": str(caminho), "categoria": "detrator", "score": 0},
    )
    assert cliente.get("/conversas").json()[0]["categoria"] == "promotor"


def test_detalhe_traz_a_transcricao(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    detalhe = cliente.get("/conversas/c1").json()
    assert len(detalhe["mensagens"]) == 3
    assert detalhe["mensagens"][0]["texto"] == "otimo"


def test_detalhe_de_conversa_inexistente_e_404(cliente):
    assert cliente.get("/conversas/nao-existe").status_code == 404


def test_indicadores_agregam_o_que_foi_importado(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    indicadores = cliente.get("/indicadores").json()
    assert indicadores["nps"] == 100.0
    assert indicadores["csat"] == 100.0
    assert indicadores["containment_rate"] == 100.0
    assert indicadores["total_conversas"] == 1


def test_indicadores_sem_dado_nao_quebra(cliente):
    indicadores = cliente.get("/indicadores").json()
    assert indicadores["total_conversas"] == 0
    # Sem score algum nao ha NPS nem CSAT: null, nunca 0 -- 0 seria um numero
    # medido apresentado no lugar de "nao medimos".
    assert indicadores["nps"] is None
    assert indicadores["csat"] is None
    # Contencao NAO depende de score, entao continua sendo um numero.
    assert indicadores["containment_rate"] == 0.0


# ---------------------------------------------------------------------------
# Ausencia de dado nao e insatisfacao: cadeia inteira com conversa sem cliente
# ---------------------------------------------------------------------------


def test_conversa_sem_fala_do_cliente_nao_vira_zero(cliente_com_sinal, tmp_path):
    caminho = tmp_path / "mudo.csv"
    caminho.write_text(CSV_SEM_CLIENTE, encoding="utf-8")
    assert (
        cliente_com_sinal.post(
            "/conversas/importar", json={"caminho": str(caminho)}
        ).status_code
        == 200
    )

    resumo = cliente_com_sinal.get("/conversas").json()[0]
    assert resumo["score"] is None
    assert resumo["categoria"] is None
    assert resumo["nota"] is None

    detalhe = cliente_com_sinal.get("/conversas/mudo").json()
    assert detalhe["score"] is None
    assert detalhe["categoria"] is None
    assert detalhe["nota"] is None

    indicadores = cliente_com_sinal.get("/indicadores").json()
    assert indicadores["nps"] is None  # nao entra em NPS
    assert indicadores["csat"] is None  # nem em CSAT
    assert indicadores["containment_rate"] == 100.0  # mas conta na contencao
    assert indicadores["total_conversas"] == 1
    assert indicadores["sem_sinal"] == 1


def test_conversa_muda_nao_derruba_o_nps_das_outras(cliente_com_sinal, tmp_path):
    com_cliente = tmp_path / "com.csv"
    com_cliente.write_text(CSV, encoding="utf-8")
    muda = tmp_path / "mudo.csv"
    muda.write_text(CSV_SEM_CLIENTE, encoding="utf-8")
    cliente_com_sinal.post("/conversas/importar", json={"caminho": str(com_cliente)})
    cliente_com_sinal.post("/conversas/importar", json={"caminho": str(muda)})

    indicadores = cliente_com_sinal.get("/indicadores").json()
    assert indicadores["nps"] == 100.0  # a muda nao entra como detratora
    assert indicadores["csat"] == 100.0
    assert indicadores["total_conversas"] == 2
    assert indicadores["sem_sinal"] == 1


# ---------------------------------------------------------------------------
# Atribuicao por sentenca
# ---------------------------------------------------------------------------


CAMPOS_PROBABILIDADE = ("prob_insatisfeito", "prob_neutro", "prob_satisfeito")


def test_atribuicao_so_traz_probabilidade_na_fala_do_cliente(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    corpo = cliente.get("/conversas/c1/atribuicao").json()
    assert corpo["conversa_id"] == "c1"
    assert corpo["score"] == 90.0
    assert corpo["nota"] == 9
    assert corpo["categoria"] == "promotor"

    for mensagem in corpo["mensagens"]:
        valores = [mensagem[campo] for campo in CAMPOS_PROBABILIDADE]
        if mensagem["autor"] == "cliente":
            assert all(isinstance(valor, float) for valor in valores)
            assert sum(valores) == pytest.approx(1.0)
        else:
            assert valores == [None, None, None]


def test_atribuicao_alinha_indice_com_a_transcricao(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    detalhe = cliente.get("/conversas/c1").json()
    atribuicao = cliente.get("/conversas/c1/atribuicao").json()

    assert len(atribuicao["mensagens"]) == len(detalhe["mensagens"])
    for indice, (na_atribuicao, na_transcricao) in enumerate(
        zip(atribuicao["mensagens"], detalhe["mensagens"])
    ):
        assert na_atribuicao["indice"] == indice
        assert na_atribuicao["texto"] == na_transcricao["texto"]
        assert na_atribuicao["autor"] == na_transcricao["autor"]


def test_atribuicao_sem_fala_do_cliente_e_tudo_nulo_sem_erro(
    cliente_com_sinal, tmp_path
):
    caminho = tmp_path / "mudo.csv"
    caminho.write_text(CSV_SEM_CLIENTE, encoding="utf-8")
    cliente_com_sinal.post("/conversas/importar", json={"caminho": str(caminho)})

    resposta = cliente_com_sinal.get("/conversas/mudo/atribuicao")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["score"] is None
    assert corpo["nota"] is None
    assert corpo["categoria"] is None
    assert corpo["mensagens"]  # a transcricao inteira continua vindo
    for mensagem in corpo["mensagens"]:
        assert [mensagem[campo] for campo in CAMPOS_PROBABILIDADE] == [None, None, None]


def test_atribuicao_de_conversa_inexistente_e_404(cliente):
    assert cliente.get("/conversas/nao-existe/atribuicao").status_code == 404


def test_atribuicao_traz_as_dezesseis_importancias(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    importancias = cliente.get("/conversas/c1/atribuicao").json()["importancias"]
    assert len(importancias) == 16
    assert set(importancias) == set(NOMES_FEATURES)


def test_atribuicao_traz_as_dezesseis_contribuicoes(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    contribuicoes = cliente.get("/conversas/c1/atribuicao").json()["contribuicoes"]
    assert contribuicoes is not None
    assert len(contribuicoes) == 16
    assert set(contribuicoes) == set(NOMES_FEATURES)


def test_atribuicao_sem_fala_do_cliente_tem_contribuicoes_nulas(
    cliente_com_sinal, tmp_path
):
    caminho = tmp_path / "mudo.csv"
    caminho.write_text(CSV_SEM_CLIENTE, encoding="utf-8")
    cliente_com_sinal.post("/conversas/importar", json={"caminho": str(caminho)})

    resposta = cliente_com_sinal.get("/conversas/mudo/atribuicao")
    assert resposta.status_code == 200
    assert resposta.json()["contribuicoes"] is None


# ---------------------------------------------------------------------------
# Robustez da importacao
# ---------------------------------------------------------------------------


def test_coluna_ausente_no_csv_e_400_nomeando_a_coluna(cliente, tmp_path):
    caminho = tmp_path / "sem_canal.csv"
    caminho.write_text(
        "conversa_id,autor,texto,enviada_em,escalou_para_humano\n"
        "c1,cliente,otimo,2026-08-13T10:00:00+00:00,false\n",
        encoding="utf-8",
    )

    resposta = cliente.post("/conversas/importar", json={"caminho": str(caminho)})
    assert resposta.status_code == 400
    assert "canal" in resposta.json()["detail"]


def test_linha_suja_e_rejeitada_com_motivo_sem_derrubar_o_lote(cliente, tmp_path):
    caminho = tmp_path / "misto.csv"
    caminho.write_text(
        "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
        "c1,csv,cliente,otimo,2026-08-13T10:00:00+00:00,false\n"
        "c2,csv,cliente,ruim,data-invalida,false\n",
        encoding="utf-8",
    )

    corpo = cliente.post(
        "/conversas/importar", json={"caminho": str(caminho)}
    ).json()
    assert corpo["importadas"] == 1
    assert corpo["rejeitadas"] == 1
    assert corpo["motivos"][0]["numero_linha"] == 3
    assert corpo["motivos"][0]["motivo"]


# ---------------------------------------------------------------------------
# A importacao nao le fora da raiz configurada
# ---------------------------------------------------------------------------


def test_caminho_relativo_que_escapa_da_raiz_e_rejeitado(cliente):
    resposta = cliente.post(
        "/conversas/importar", json={"caminho": "../../algo.csv"}
    )
    assert resposta.status_code == 400
    assert "fora da raiz" in resposta.json()["detail"]


def test_caminho_absoluto_fora_da_raiz_e_rejeitado(cliente, tmp_path_factory):
    fora = tmp_path_factory.mktemp("fora") / "segredo.csv"
    fora.write_text(CSV, encoding="utf-8")

    resposta = cliente.post("/conversas/importar", json={"caminho": str(fora)})
    assert resposta.status_code == 400
    assert "fora da raiz" in resposta.json()["detail"]


def test_caminho_relativo_dentro_da_raiz_e_aceito(cliente, tmp_path):
    (tmp_path / "entrada.csv").write_text(CSV, encoding="utf-8")

    resposta = cliente.post("/conversas/importar", json={"caminho": "entrada.csv"})
    assert resposta.status_code == 200
    assert resposta.json()["importadas"] == 1
