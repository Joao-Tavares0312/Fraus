import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.fusor import NOMES_FEATURES
from fraus.indicadores import FAIXAS_NPS
from fraus.sinais.emoji import emojis_com_posicao, score_do_emoji
from fraus.sinais.estilo import estilo_da_mensagem
from fraus.sinais.palavras import PALAVRA, vocabulario

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

    def importancias(self) -> dict:
        return {nome: 1.0 for nome in NOMES_FEATURES}

    def eixo_global(self) -> dict:
        """Peso global com sinal, determinístico -- sem fusor treinado de verdade."""
        return {nome: float((indice % 5) - 2) for indice, nome in enumerate(NOMES_FEATURES)}

    def analisar_conversa(self, conversa, referencia=None) -> dict:
        """Analise avulsa do dublê: peso de palavra deterministico, sem modelo.

        O peso e o comprimento da palavra dividido por dez, com sinal positivo
        -- numero sem significado nenhum, so com a FORMA certa. O que os testes
        de `/analisar` verificam e a mecanica da rota (nada e gravado, o que
        ficou de fora e relatado, so a fala do cliente recebe peso), e nao a
        opiniao do BERTimbau, que muda a cada retreino.
        """
        atribuicao = self.atribuir_conversa(conversa)
        for mensagem in atribuicao["mensagens"]:
            if mensagem["autor"] != "cliente":
                mensagem["palavras"] = None
                continue
            mensagem["palavras"] = [
                {
                    "palavra": achado.group(),
                    "inicio": achado.start(),
                    "fim": achado.end(),
                    "peso": len(achado.group()) / 10,
                }
                for achado in PALAVRA.finditer(mensagem["texto"])
            ]
        return {
            **atribuicao,
            "score": self.pontuar_conversa(conversa),
            "vocabulario": vocabulario(conversa, referencia),
        }

    def simular_texto(self, texto: str) -> dict:
        p = _probabilidades_deterministicas(texto)
        emojis = [
            {"emoji": emoji, "score": score_do_emoji(emoji), "posicao_relativa": posicao}
            for emoji, posicao in emojis_com_posicao(texto)
        ]
        return {
            "prob_insatisfeito": p[0],
            "prob_neutro": p[1],
            "prob_satisfeito": p[2],
            "emojis": emojis,
            # Estilo e deterministico (regra, nao classificador), entao o
            # duble usa a funcao real -- nao ha o que dublar.
            "estilo": estilo_da_mensagem(texto),
        }


class MotorFalso(AtribuicaoDuble):
    def pontuar_conversa(self, conversa, curadoria=None):
        return 90.0


class MotorRespeitandoSinal(AtribuicaoDuble):
    """Duble que honra o invariante do Motor real: sem fala do cliente, sem score."""

    def pontuar_conversa(self, conversa, curadoria=None):
        if not conversa.tem_sinal_cliente:
            return None  # ausencia de dado nao e insatisfacao
        return 90.0


@pytest.fixture
def cliente(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return TestClient(
        criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path)
    )


@pytest.fixture
def cliente_com_sinal(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
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
    # A conversa do CSV sai promotora e foi contida: sucesso de verdade.
    assert indicadores["falso_containment"] == 0.0
    assert indicadores["contidos_com_score"] == 1
    assert indicadores["total_conversas"] == 1


def test_indicadores_sem_dado_nao_quebra(cliente):
    indicadores = cliente.get("/indicadores").json()
    assert indicadores["total_conversas"] == 0
    # Sem score algum nao ha NPS nem CSAT: null, nunca 0 -- 0 seria um numero
    # medido apresentado no lugar de "nao medimos".
    assert indicadores["nps"] is None
    assert indicadores["csat"] is None
    # A CONTENCAO TAMBEM E None NO CONJUNTO VAZIO -- mudou em 10/09/2026.
    #
    # O comentario aqui defendia `0.0` com um raciocinio CERTO: contencao nao
    # depende de score, entao ela continua medida quando NPS e CSAT nao estao
    # (ver `test_conversa_sem_fala_do_cliente_nao_vira_zero`, que segue
    # exigindo 100%). Esse caso nao mudou e nao pode mudar.
    #
    # O que estava errado e o conjunto VAZIO, onde nada foi medido. A prova de
    # que alguem ja tinha sentido isso estava no front: `page.tsx` escrevia
    # `total_conversas ? containment_rate : null`, ou seja, o cliente nao
    # acreditava no numero do servidor. Servidor e cliente discordando sobre o
    # mesmo campo, e nada explicando por que -- e qualquer consumidor que nao
    # fosse a dashboard (export, webhook, terceiro lendo /indicadores) recebia
    # "0% de contencao", o pior numero da escala, para um conjunto vazio.
    assert indicadores["containment_rate"] is None
    # Falso containment PRECISA de score: sem nenhum contido pontuado nao ha
    # o que afirmar, e 0.0 se leria como "nenhum contido saiu insatisfeito".
    assert indicadores["falso_containment"] is None
    assert indicadores["contidos_com_score"] == 0


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
    # ...e fica FORA do falso containment, que so fala de quem tem score.
    assert indicadores["falso_containment"] is None
    assert indicadores["contidos_com_score"] == 0
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


def test_atribuicao_traz_as_trinta_e_nove_importancias(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    importancias = cliente.get("/conversas/c1/atribuicao").json()["importancias"]
    assert len(importancias) == 39
    assert set(importancias) == set(NOMES_FEATURES)


def test_atribuicao_traz_as_trinta_e_nove_contribuicoes(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    contribuicoes = cliente.get("/conversas/c1/atribuicao").json()["contribuicoes"]
    assert contribuicoes is not None
    assert len(contribuicoes) == 39
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


# ---------------------------------------------------------------------------
# /modelo -- ficha do modelo (importancias, metricas, faixas, lexicon)
# ---------------------------------------------------------------------------


def test_modelo_traz_as_trinta_e_nove_importancias_e_as_faixas_corretas(cliente):
    corpo = cliente.get("/modelo").json()
    assert len(corpo["importancias"]) == 39
    assert set(corpo["importancias"]) == set(NOMES_FEATURES)
    assert corpo["classes"] == ["insatisfeito", "neutro", "satisfeito"]
    assert corpo["faixas_nps"] == {
        categoria: list(faixa) for categoria, faixa in FAIXAS_NPS.items()
    }


def test_modelo_sem_arquivo_de_metricas_devolve_null(cliente, tmp_path, monkeypatch):
    import fraus.api.rotas.modelo as main_module

    monkeypatch.setattr(main_module, "CAMINHO_METRICAS", tmp_path / "nao-existe.json")
    corpo = cliente.get("/modelo").json()
    assert corpo["metricas"] is None


def test_modelo_traz_metricas_quando_arquivo_existe(cliente, tmp_path, monkeypatch):
    import fraus.api.rotas.modelo as main_module

    caminho_metricas = tmp_path / "metricas.json"
    caminho_metricas.write_text('{"acuracia": 0.9, "f1_macro": 0.88}', encoding="utf-8")
    monkeypatch.setattr(main_module, "CAMINHO_METRICAS", caminho_metricas)

    corpo = cliente.get("/modelo").json()
    assert corpo["metricas"] == {"acuracia": 0.9, "f1_macro": 0.88}


def test_modelo_traz_total_de_emojis_do_lexicon(cliente):
    corpo = cliente.get("/modelo").json()
    assert corpo["total_emojis_lexicon"] > 0


# ---------------------------------------------------------------------------
# /modelo/lexicon
# ---------------------------------------------------------------------------


def test_lexicon_respeita_limite_e_deslocamento(cliente):
    pagina1 = cliente.get("/modelo/lexicon?limite=5&deslocamento=0").json()
    pagina2 = cliente.get("/modelo/lexicon?limite=5&deslocamento=5").json()
    assert len(pagina1["itens"]) == 5
    assert len(pagina2["itens"]) == 5
    assert pagina1["total"] == pagina2["total"]
    assert pagina1["itens"] != pagina2["itens"]


def test_lexicon_tem_teto_de_200_mesmo_pedindo_mais(cliente):
    corpo = cliente.get("/modelo/lexicon?limite=10000").json()
    assert len(corpo["itens"]) <= 200


def test_lexicon_busca_por_emoji_conhecido_acha(cliente):
    corpo = cliente.get("/modelo/lexicon?busca=😂").json()
    assert corpo["total"] >= 1
    assert any(item["emoji"] == "😂" for item in corpo["itens"])


def test_lexicon_busca_sem_resultado_devolve_lista_vazia(cliente):
    corpo = cliente.get("/modelo/lexicon?busca=🛸🛸🛸-nao-existe").json()
    assert corpo["total"] == 0
    assert corpo["itens"] == []


def test_lexicon_score_bate_com_score_do_emoji_direto(cliente):
    corpo = cliente.get("/modelo/lexicon?busca=😂").json()
    item = corpo["itens"][0]
    assert item["score"] == pytest.approx(score_do_emoji("😂"))


# ---------------------------------------------------------------------------
# /modelo/simular
# ---------------------------------------------------------------------------


def test_simular_devolve_as_tres_probabilidades(cliente):
    corpo = cliente.post("/modelo/simular", json={"texto": "otimo atendimento"}).json()
    assert corpo["texto"] == "otimo atendimento"
    total = corpo["prob_insatisfeito"] + corpo["prob_neutro"] + corpo["prob_satisfeito"]
    assert total == pytest.approx(1.0)


def test_simular_com_texto_vazio_e_400(cliente):
    assert cliente.post("/modelo/simular", json={"texto": ""}).status_code == 400
    assert cliente.post("/modelo/simular", json={"texto": "   "}).status_code == 400


def test_simular_com_texto_acima_do_teto_e_400(cliente):
    texto_longo = "a" * 2001
    assert cliente.post("/modelo/simular", json={"texto": texto_longo}).status_code == 400


def test_simular_no_teto_exato_e_aceito(cliente):
    texto_no_teto = "a" * 2000
    resposta = cliente.post("/modelo/simular", json={"texto": texto_no_teto})
    assert resposta.status_code == 200


def test_simular_devolve_estilo_da_frase(cliente):
    """A rota escolhia as chaves a dedo e esquecia `estilo` -- o motor ja o
    calculava (`fraus.motor.Motor.simular_texto`), mas a rota nunca o
    repassava. O Simulador da dashboard depende deste campo (Task 10)."""
    corpo = cliente.post(
        "/modelo/simular", json={"texto": "ISSO E UM ABSURDO!!! naaaao acredito"}
    ).json()
    assert corpo["estilo"]["caixa_alta"] is True
    assert corpo["estilo"]["alongamento"] is True
    assert corpo["estilo"]["pontuacao_enfatica"] >= 1


def test_simular_com_emoji_devolve_posicao_relativa(cliente):
    corpo = cliente.post("/modelo/simular", json={"texto": "muito bom 😄"}).json()
    assert len(corpo["emojis"]) == 1
    assert corpo["emojis"][0]["emoji"] == "😄"
    assert isinstance(corpo["emojis"][0]["posicao_relativa"], float)


def test_navegador_da_dashboard_recebe_liberacao_de_origem(cliente):
    """A dashboard chama a API do NAVEGADOR: sem CORS o pedido nem sai.

    O simulador e o indicador de saude rodam no cliente, entao uma resposta
    200 sem `access-control-allow-origin` chega na tela como "Failed to fetch".
    Servidor-para-servidor (o render do Next) nao passa por essa checagem, o
    que faz a falha aparecer SO em parte das telas -- e foi assim que ela
    apareceu.
    """
    resposta = cliente.post(
        "/modelo/simular",
        json={"texto": "otimo atendimento"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_origem_desconhecida_nao_e_liberada(cliente):
    """A liberacao e uma lista, nao `*`: a API le o banco de atendimentos."""
    resposta = cliente.post(
        "/modelo/simular",
        json={"texto": "otimo atendimento"},
        headers={"Origin": "http://sitio-qualquer.example"},
    )
    assert "access-control-allow-origin" not in resposta.headers


# --- Configuracoes ----------------------------------------------------------

FAIXAS_ALTERNATIVAS = {"detrator": [0, 7], "neutro": [8, 9], "promotor": [10, 10]}


def test_configuracoes_devolve_vigente_e_de_fabrica(cliente):
    """A tela precisa dos dois para poder oferecer 'voltar ao padrao'."""
    corpo = cliente.get("/configuracoes").json()
    assert corpo["vigente"] == corpo["fabrica"]
    assert corpo["fabrica"]["faixas_nps"] == {
        categoria: list(faixa) for categoria, faixa in FAIXAS_NPS.items()
    }
    assert corpo["fabrica"]["limiares_latencia_s"] == [10, 60, 180]


def test_put_configuracoes_grava_e_a_leitura_reflete(cliente):
    resposta = cliente.put("/configuracoes", json={"limiares_latencia_s": [5, 30, 90]})
    assert resposta.status_code == 200
    assert resposta.json()["vigente"]["limiares_latencia_s"] == [5, 30, 90]
    assert cliente.get("/configuracoes").json()["vigente"]["limiares_latencia_s"] == [5, 30, 90]
    # fabrica nao se mexe: e o alvo do "voltar ao padrao"
    assert cliente.get("/configuracoes").json()["fabrica"]["limiares_latencia_s"] == [10, 60, 180]


@pytest.mark.parametrize("corpo,trecho", [
    ({"faixas_nps": {"detrator": [0, 5], "neutro": [7, 8], "promotor": [9, 10]}}, "buraco"),
    ({"faixas_nps": {"detrator": [0, 7], "neutro": [7, 8], "promotor": [9, 10]}}, "sobrepoe"),
    ({"faixas_nps": {"detrator": [0, 6], "neutro": [8, 7], "promotor": [9, 10]}}, "vazia"),
    ({"limiares_latencia_s": [180, 60, 10]}, "crescente"),
    ({"cor_do_botao": "azul"}, "cor_do_botao"),
])
def test_configuracao_invalida_e_400_nomeando_o_problema(cliente, corpo, trecho):
    resposta = cliente.put("/configuracoes", json=corpo)
    assert resposta.status_code == 400
    assert trecho in resposta.json()["detail"]


def test_configuracao_recusada_nao_deixa_rastro(cliente):
    cliente.put("/configuracoes", json={"limiares_latencia_s": [180, 60, 10]})
    assert cliente.get("/configuracoes").json()["vigente"]["limiares_latencia_s"] == [10, 60, 180]


def test_faixa_configurada_muda_a_categoria_de_atendimento_ja_pontuado(cliente, tmp_path):
    """Categoria e DERIVADA NA LEITURA: score gravado, faixa vigente."""
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})
    assert cliente.get("/conversas").json()[0]["categoria"] == "promotor"

    cliente.put("/configuracoes", json={"faixas_nps": FAIXAS_ALTERNATIVAS})

    assert cliente.get("/conversas").json()[0]["categoria"] == "neutro"
    assert cliente.get("/conversas/c1").json()["categoria"] == "neutro"
    assert cliente.get("/conversas/c1/atribuicao").json()["categoria"] == "neutro"
    # o score, esse sim resultado do modelo, nao se mexe
    assert cliente.get("/conversas/c1").json()["score"] == 90.0


def test_indicadores_e_conversas_nao_discordam_apos_mudar_a_faixa(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})
    assert cliente.get("/indicadores").json()["nps"] == 100.0  # 1 promotor

    cliente.put("/configuracoes", json={"faixas_nps": FAIXAS_ALTERNATIVAS})

    assert cliente.get("/conversas").json()[0]["categoria"] == "neutro"
    assert cliente.get("/indicadores").json()["nps"] == 0.0  # nem promotor nem detrator


def test_modelo_publica_a_faixa_vigente_e_nao_a_de_fabrica(cliente):
    """`/modelo` e a categoria bebem da MESMA fonte -- faixa duplicada foi bug uma vez."""
    cliente.put("/configuracoes", json={"faixas_nps": FAIXAS_ALTERNATIVAS})
    assert cliente.get("/modelo").json()["faixas_nps"] == FAIXAS_ALTERNATIVAS


# --- Integracoes: fontes ----------------------------------------------------

FONTE = {"nome": "Planilha do suporte", "canal": "webchat", "tipo": "csv"}


def test_criar_e_listar_fonte(cliente):
    resposta = cliente.post("/integracoes/fontes", json=FONTE)
    assert resposta.status_code == 201
    criada = resposta.json()
    assert criada["nome"] == FONTE["nome"]
    assert criada["ativa"] is True
    assert criada["criada_em"]

    listagem = cliente.get("/integracoes/fontes").json()
    assert [f["id"] for f in listagem] == [criada["id"]]


@pytest.mark.parametrize("corpo,trecho", [
    ({"nome": "   ", "canal": "webchat", "tipo": "csv"}, "nome"),
    ({"nome": "x", "canal": "webchat", "tipo": "carteiro"}, "carteiro"),
])
def test_fonte_invalida_e_400_nomeando_o_problema(cliente, corpo, trecho):
    resposta = cliente.post("/integracoes/fontes", json=corpo)
    assert resposta.status_code == 400
    assert trecho in resposta.json()["detail"]


def test_fonte_expoe_se_o_segredo_esta_configurado_nunca_o_valor(cliente, monkeypatch):
    """Segredo mora na variavel de ambiente; o banco guarda so o NOME dela."""
    monkeypatch.delenv("FRAUS_TESTE_TOKEN", raising=False)
    corpo = {**FONTE, "tipo": "webhook", "variavel_segredo": "FRAUS_TESTE_TOKEN"}
    criada = cliente.post("/integracoes/fontes", json=corpo).json()
    assert criada["variavel_segredo"] == "FRAUS_TESTE_TOKEN"
    assert criada["configurada"] is False

    monkeypatch.setenv("FRAUS_TESTE_TOKEN", "segredo-de-verdade")
    listada = cliente.get("/integracoes/fontes").json()[0]
    assert listada["configurada"] is True
    assert "segredo-de-verdade" not in cliente.get("/integracoes/fontes").text


def test_fonte_sem_variavel_de_segredo_nao_finge_estar_configurada(cliente):
    criada = cliente.post("/integracoes/fontes", json=FONTE).json()
    assert criada["variavel_segredo"] is None
    assert criada["configurada"] is False


def test_patch_renomeia_e_desativa_a_fonte(cliente):
    criada = cliente.post("/integracoes/fontes", json=FONTE).json()
    resposta = cliente.patch(
        f"/integracoes/fontes/{criada['id']}", json={"nome": "Outro nome", "ativa": False}
    )
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Outro nome"
    assert resposta.json()["ativa"] is False
    assert cliente.get("/integracoes/fontes").json()[0]["ativa"] is False


def test_patch_com_nome_vazio_e_400(cliente):
    criada = cliente.post("/integracoes/fontes", json=FONTE).json()
    resposta = cliente.patch(f"/integracoes/fontes/{criada['id']}", json={"nome": " "})
    assert resposta.status_code == 400
    assert "nome" in resposta.json()["detail"]


def test_patch_e_delete_de_fonte_inexistente_sao_404(cliente):
    assert cliente.patch("/integracoes/fontes/999", json={"ativa": False}).status_code == 404
    assert cliente.delete("/integracoes/fontes/999").status_code == 404


def test_apagar_fonte_nao_apaga_conversa_nenhuma(cliente, tmp_path):
    """Fonte e cadastro de origem, nao dona do dado que ja entrou."""
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})
    criada = cliente.post("/integracoes/fontes", json=FONTE).json()

    assert cliente.delete(f"/integracoes/fontes/{criada['id']}").status_code == 204

    assert cliente.get("/integracoes/fontes").json() == []
    assert len(cliente.get("/conversas").json()) == 1


# --- Integracoes: historico de importacoes ----------------------------------

CSV_COM_LINHA_SUJA = (
    "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
    "c1,csv,cliente,otimo,2026-08-13T10:00:00+00:00,false\n"
    "c2,csv,cliente,oi,data-invalida,false\n"
)


def test_historico_comeca_vazio_e_nao_inventa_importacao(cliente):
    assert cliente.get("/integracoes/importacoes").json() == []


def test_importar_registra_o_que_entrou_e_o_que_ficou_de_fora(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV_COM_LINHA_SUJA, encoding="utf-8")
    resposta = cliente.post("/conversas/importar", json={"caminho": str(caminho)}).json()

    historico = cliente.get("/integracoes/importacoes").json()
    assert len(historico) == 1
    registro = historico[0]
    assert registro["arquivo"] == "entrada.csv"
    assert registro["aceitas"] == resposta["importadas"]
    assert registro["rejeitadas"] == resposta["rejeitadas"]
    assert registro["rejeitadas"] > 0
    assert registro["motivos"] == resposta["motivos"]
    assert registro["ocorrida_em"]


def test_historico_vem_com_a_importacao_mais_recente_primeiro(cliente, tmp_path):
    primeiro = tmp_path / "primeiro.csv"
    primeiro.write_text(CSV, encoding="utf-8")
    segundo = tmp_path / "segundo.csv"
    segundo.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(primeiro)})
    cliente.post("/conversas/importar", json={"caminho": str(segundo)})

    arquivos = [r["arquivo"] for r in cliente.get("/integracoes/importacoes").json()]
    assert arquivos == ["segundo.csv", "primeiro.csv"]


def test_importacao_recusada_por_esquema_nao_entra_no_historico(cliente, tmp_path):
    """Historico e do que a ingestao processou -- arquivo recusado na porta nao e."""
    caminho = tmp_path / "sem_coluna.csv"
    caminho.write_text("conversa_id,canal\nc1,csv\n", encoding="utf-8")
    assert cliente.post("/conversas/importar", json={"caminho": str(caminho)}).status_code == 400
    assert cliente.get("/integracoes/importacoes").json() == []


# --- GET /serie-temporal ----------------------------------------------------

CSV_TRES_DIAS = (
    "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
    "d1,csv,cliente,otimo,2026-08-13T10:00:00+00:00,false\n"
    "d1,csv,bot,de nada,2026-08-13T10:00:10+00:00,false\n"
    "d2,csv,cliente,otimo,2026-08-14T10:00:00+00:00,false\n"
    "d2,csv,bot,de nada,2026-08-14T10:00:20+00:00,false\n"
    "d3,csv,cliente,otimo,2026-08-15T10:00:00+00:00,false\n"
    "d3,csv,bot,de nada,2026-08-15T10:00:30+00:00,false\n"
)


def _semear_tres_dias(cliente, tmp_path):
    caminho = tmp_path / "tres_dias.csv"
    caminho.write_text(CSV_TRES_DIAS, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": "tres_dias.csv"})


def test_serie_temporal_sem_recorte_traz_todos_os_dias(cliente, tmp_path):
    _semear_tres_dias(cliente, tmp_path)
    corpo = cliente.get("/serie-temporal").json()
    assert [p["dia"] for p in corpo["pontos"]] == [
        "2026-08-13", "2026-08-14", "2026-08-15"
    ]
    assert corpo["de"] is None and corpo["ate"] is None


def test_recorte_e_inclusivo_nas_duas_pontas(cliente, tmp_path):
    """`de` e `ate` entram na resposta -- e assim que quem opera le o periodo."""
    _semear_tres_dias(cliente, tmp_path)
    corpo = cliente.get("/serie-temporal?de=2026-08-13&ate=2026-08-14").json()
    assert [p["dia"] for p in corpo["pontos"]] == ["2026-08-13", "2026-08-14"]


def test_latencia_por_dia_sai_dos_timestamps(cliente, tmp_path):
    _semear_tres_dias(cliente, tmp_path)
    pontos = cliente.get("/serie-temporal").json()["pontos"]
    assert [p["latencia_mediana_s"] for p in pontos] == [10.0, 20.0, 30.0]


def test_data_malformada_e_400_nomeando_o_parametro(cliente):
    """Filtro invalido nao pode ser ignorado: devolveria a serie inteira
    parecendo o recorte pedido."""
    resposta = cliente.get("/serie-temporal?de=13/08/2026")
    assert resposta.status_code == 400
    assert "de" in resposta.json()["detail"]


def test_periodo_invertido_e_400(cliente):
    resposta = cliente.get("/serie-temporal?de=2026-08-15&ate=2026-08-13")
    assert resposta.status_code == 400
    assert "invertido" in resposta.json()["detail"]


def test_serie_respeita_a_faixa_configurada(cliente, tmp_path):
    """Mesma regra do resto da API: a categoria e derivada na LEITURA.

    A faixa e montada em volta da nota que o duble deu -- fixar numeros aqui
    testaria o duble, nao a derivacao.
    """
    _semear_tres_dias(cliente, tmp_path)
    # O duble da nota 9 -- promotor na faixa de fabrica (9-10).
    assert cliente.get("/serie-temporal").json()["pontos"][0]["nps"] == 100.0

    # Estreitar promotor para 10 joga essa nota em neutro: o NPS do MESMO dado
    # cai para 0 sem nenhum score ter sido recalculado.
    resposta = cliente.put("/configuracoes", json={
        "faixas_nps": {"detrator": [0, 8], "neutro": [9, 9], "promotor": [10, 10]}
    })
    assert resposta.status_code == 200
    assert cliente.get("/serie-temporal").json()["pontos"][0]["nps"] == 0.0


# --- GET /integracoes/tipos e /integracoes/arquivos -------------------------


def test_tipos_de_fonte_sao_os_mesmos_que_o_post_aceita(cliente):
    """A lista publicada e a lista validada: se divergirem, o formulario
    oferece um tipo que a criacao recusa."""
    from fraus.api.main import TIPOS_DE_FONTE

    publicados = {t["valor"] for t in cliente.get("/integracoes/tipos").json()}
    assert publicados == set(TIPOS_DE_FONTE)


def test_cada_tipo_publicado_e_de_fato_aceito_na_criacao(cliente):
    for tipo in cliente.get("/integracoes/tipos").json():
        resposta = cliente.post(
            "/integracoes/fontes",
            json={"nome": f"fonte {tipo['valor']}", "canal": "webchat", "tipo": tipo["valor"]},
        )
        assert resposta.status_code == 201, resposta.json()


def test_arquivos_lista_csv_da_raiz_com_caminho_relativo(cliente, tmp_path):
    (tmp_path / "agosto").mkdir()
    (tmp_path / "raiz.csv").write_text(CSV, encoding="utf-8")
    (tmp_path / "agosto" / "semana1.csv").write_text(CSV, encoding="utf-8")

    corpo = cliente.get("/integracoes/arquivos").json()
    caminhos = {a["caminho"] for a in corpo["arquivos"]}
    assert caminhos == {"raiz.csv", "agosto/semana1.csv"}


def test_arquivos_nao_vaza_caminho_absoluto(cliente, tmp_path):
    """Quem opera nao precisa saber onde a pasta fica no disco, e a resposta
    nao deve descrever a arvore da maquina."""
    (tmp_path / "entrada.csv").write_text(CSV, encoding="utf-8")
    corpo = cliente.get("/integracoes/arquivos").json()
    for arquivo in corpo["arquivos"]:
        assert not arquivo["caminho"].startswith("/")
        assert ":" not in arquivo["caminho"]  # C:\ do Windows
        assert str(tmp_path) not in arquivo["caminho"]


def test_arquivo_listado_pode_ser_importado_direto(cliente, tmp_path):
    """O contrato entre as duas rotas: o que a listagem devolve serve, sem
    ajuste, como `caminho` da importacao."""
    (tmp_path / "agosto").mkdir()
    (tmp_path / "agosto" / "lote.csv").write_text(CSV, encoding="utf-8")

    (arquivo,) = cliente.get("/integracoes/arquivos").json()["arquivos"]
    resposta = cliente.post(
        "/conversas/importar", json={"caminho": arquivo["caminho"]}
    )
    assert resposta.status_code == 200
    assert resposta.json()["importadas"] == 1


def test_raiz_sem_csv_devolve_lista_vazia_e_nao_erro(cliente):
    corpo = cliente.get("/integracoes/arquivos").json()
    assert corpo["arquivos"] == []


# ---------------------------------------------------------------------------
# /analisar -- exame de um atendimento avulso, sem gravar nada


def test_analisar_nao_grava_a_conversa_no_banco(cliente_com_sinal):
    """A diferenca entre esta rota e a importacao: analisar nao muda o NPS.

    Se a conversa analisada entrasse no banco, bastaria examinar um atendimento
    ruim para a operacao inteira piorar nos indicadores -- e o operador nao
    teria pedido isso em lugar nenhum.
    """
    antes = cliente_com_sinal.get("/indicadores").json()

    resposta = cliente_com_sinal.post("/analisar", json={"csv": CSV})
    assert resposta.status_code == 200

    assert cliente_com_sinal.get("/conversas").json() == []
    assert cliente_com_sinal.get("/indicadores").json() == antes


def test_analisar_devolve_peso_so_na_fala_do_cliente(cliente_com_sinal):
    """Pontuar o roteiro do bot seria numero bonito e sem lastro."""
    corpo = cliente_com_sinal.post("/analisar", json={"csv": CSV}).json()
    mensagens = corpo["analises"][0]["mensagens"]

    for mensagem in mensagens:
        if mensagem["autor"] == "cliente":
            assert mensagem["palavras"], "fala do cliente tem que ter peso"
        else:
            assert mensagem["palavras"] is None


def test_analisar_traz_a_ficha_operacional_da_conversa(cliente_com_sinal):
    """Mesma funcao de `/conversas`: a analise nao pode discordar da lista."""
    corpo = cliente_com_sinal.post("/analisar", json={"csv": CSV}).json()
    analise = corpo["analises"][0]

    assert analise["qtd_mensagens"] == 3
    assert analise["qtd_cliente"] == 2
    assert analise["desfecho"] == "sem_resposta"  # a ultima fala e do cliente
    assert analise["latencia_primeira_resposta_s"] == 8.0


def test_analisar_conversa_muda_nao_inventa_nota(cliente_com_sinal):
    corpo = cliente_com_sinal.post("/analisar", json={"csv": CSV_SEM_CLIENTE}).json()
    analise = corpo["analises"][0]

    assert analise["score"] is None
    assert analise["nota"] is None
    assert analise["categoria"] is None
    assert analise["desfecho"] == "sem_sinal"
    assert analise["vocabulario"] == []


def test_analisar_arquivo_vazio_e_400(cliente_com_sinal):
    resposta = cliente_com_sinal.post("/analisar", json={"csv": "   \n  "})
    assert resposta.status_code == 400


def test_analisar_sem_conversa_valida_explica_o_formato_esperado(cliente_com_sinal):
    """Recusar sem dizer o que se esperava obriga o operador a adivinhar."""
    so_cabecalho = "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
    resposta = cliente_com_sinal.post("/analisar", json={"csv": so_cabecalho})

    assert resposta.status_code == 400
    assert "conversa_id" in resposta.json()["detail"]


def test_analisar_sem_coluna_opcional_entra_pelo_mapeador(cliente_com_sinal):
    """Desde 14/09/2026 `canal` e opcional: o mapeador acha os papeis e RELATA."""
    sem_canal = (
        "conversa_id,autor,texto,enviada_em,escalou_para_humano\n"
        "c1,cliente,otimo,2026-08-13T10:00:00+00:00,false\n"
    )
    resposta = cliente_com_sinal.post("/analisar", json={"csv": sem_canal})

    assert resposta.status_code == 200
    assert "inferidas" in resposta.json()["formato"]


def test_analisar_sem_papel_obrigatorio_nomeia_o_que_falta(cliente_com_sinal):
    """Arquivo sem fala mapeavel e defeito do ARQUIVO -- 400 nomeando, nunca 500 cru."""
    resposta = cliente_com_sinal.post("/analisar", json={"csv": "id,valor\n1,10\n2,20\n"})

    assert resposta.status_code == 400
    assert "texto" in resposta.json()["detail"]


def test_analisar_relata_a_linha_rejeitada_em_vez_de_derrubar_o_arquivo(
    cliente_com_sinal,
):
    com_lixo = CSV + "c1,csv,cliente,texto,data-invalida,false\n"
    corpo = cliente_com_sinal.post("/analisar", json={"csv": com_lixo}).json()

    assert corpo["total_rejeitadas"] == 1
    assert corpo["rejeitadas"][0]["numero_linha"] == 5
    assert corpo["analises"], "a conversa valida tem que sobreviver a linha ruim"


def test_analisar_relata_quando_corta_conversas_do_arquivo(cliente_com_sinal):
    """Silenciar o corte faria o operador achar que analisou o arquivo inteiro."""
    from fraus.api.main import TETO_CONVERSAS_ANALISE

    linhas = ["conversa_id,canal,autor,texto,enviada_em,escalou_para_humano"]
    for indice in range(TETO_CONVERSAS_ANALISE + 3):
        linhas.append(
            f"c{indice},csv,cliente,otimo,2026-08-13T10:00:00+00:00,false"
        )
    corpo = cliente_com_sinal.post("/analisar", json={"csv": "\n".join(linhas)}).json()

    assert corpo["conversas_no_arquivo"] == TETO_CONVERSAS_ANALISE + 3
    assert corpo["conversas_analisadas"] == TETO_CONVERSAS_ANALISE
    assert len(corpo["analises"]) == TETO_CONVERSAS_ANALISE


def test_analisar_arquivo_grande_demais_e_recusado_antes_de_rodar_o_modelo(
    cliente_com_sinal,
):
    """A oclusao roda uma passada por palavra: sem teto, a requisicao pendura."""
    from fraus.api.main import TETO_ARQUIVO_ANALISE

    resposta = cliente_com_sinal.post(
        "/analisar", json={"csv": "x" * (TETO_ARQUIVO_ANALISE + 1)}
    )
    assert resposta.status_code == 400
    assert "limite" in resposta.json()["detail"]


def test_modelo_publica_as_tres_cabecas_marcando_quem_pontua(cliente):
    """`pontua` diz se a cabeca entra no fusor.

    Ate 03/09/2026 as tres valiam `True`. Desde 04/09/2026 a ironia saiu do
    vetor (o corpus de treino faz a cabeca funcionar como detector de
    sentimento positivo, nao de ironia -- ver `fraus/fusor.py`) e passou a
    marcar `False`: ela continua carregada e lida por mensagem, so nao decide
    mais a nota. E exatamente o caso que este campo existe para distinguir.
    """
    corpo = cliente.get("/modelo").json()
    por_nome = {cabeca["nome"]: cabeca for cabeca in corpo["cabecas"]}

    assert set(por_nome) == {"satisfacao", "emocao", "ironia"}
    assert por_nome["satisfacao"]["pontua"] is True
    assert por_nome["emocao"]["pontua"] is True
    assert por_nome["ironia"]["pontua"] is False


def test_cabeca_sem_metricas_exportadas_vem_null_e_nao_zerada(cliente, tmp_path, monkeypatch):
    """Antes do treino, `null`. Zero seria dizer que a cabeca erra tudo."""
    from fraus.api.rotas import modelo as main_module

    monkeypatch.setattr(main_module, "CAMINHO_METRICAS_IRONIA", tmp_path / "nao-existe.json")
    corpo = cliente.get("/modelo").json()
    ironia = next(c for c in corpo["cabecas"] if c["nome"] == "ironia")

    assert ironia["metricas"] is None


def test_cabeca_de_emocao_declara_o_desprezo_como_derivado(cliente):
    """Sao oito classes: as sete treinadas mais a diade raiva+nojo."""
    corpo = cliente.get("/modelo").json()
    emocao = next(c for c in corpo["cabecas"] if c["nome"] == "emocao")

    assert emocao["classes"][-1] == "desprezo"
    assert len(emocao["classes"]) == 8


# ---------------------------------------------------------------------------
# /analisar/arquivo -- csv, xlsx, docx e pdf


def _docx_bytes(texto: str) -> bytes:
    import io as _io

    import docx

    documento = docx.Document()
    for linha in texto.splitlines():
        documento.add_paragraph(linha)
    buffer = _io.BytesIO()
    documento.save(buffer)
    return buffer.getvalue()


def test_upload_de_csv_analisa_sem_gravar(cliente_com_sinal):
    resposta = cliente_com_sinal.post(
        "/analisar/arquivo",
        files={"arquivo": ("conversa.csv", CSV.encode("utf-8"), "text/csv")},
    )
    assert resposta.status_code == 200
    assert resposta.json()["analises"]
    assert cliente_com_sinal.get("/conversas").json() == []


def test_transcricao_sem_horario_nao_recebe_nota(cliente_com_sinal):
    """Zerar a latencia faria o fusor ler como resposta instantanea.

    Latencia e uma das 39 features, com peso aprendido: sem horario o
    modelo veria toda resposta como imediata e a nota sairia melhor do que a
    verdade, sem erro nenhum aparecer. A ausencia da nota E a resposta honesta.
    """
    transcricao = (
        "Cliente: minha cobranca veio duplicada\n"
        "Bot: vou verificar\n"
        "Cliente: obrigado\n"
    )
    corpo = cliente_com_sinal.post(
        "/analisar/arquivo",
        files={
            "arquivo": (
                "conversa.docx",
                _docx_bytes(transcricao),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    ).json()

    assert corpo["tem_tempo"] is False
    analise = corpo["analises"][0]
    assert analise["score"] is None
    assert analise["nota"] is None
    assert analise["categoria"] is None
    # A leitura por mensagem NAO depende de tempo e continua valendo.
    assert any(m["palavras"] for m in analise["mensagens"])
    assert any("latência" in aviso for aviso in corpo["avisos"])


def test_upload_declara_como_o_arquivo_foi_entendido(cliente_com_sinal):
    """Analise cuja procedencia nao aparece e numero sem lastro."""
    corpo = cliente_com_sinal.post(
        "/analisar/arquivo",
        files={"arquivo": ("conversa.csv", CSV.encode("utf-8"), "text/csv")},
    ).json()
    assert "Fraus" in corpo["formato"]
    assert corpo["tem_tempo"] is True


def test_upload_de_formato_desconhecido_e_400_listando_os_aceitos(cliente_com_sinal):
    resposta = cliente_com_sinal.post(
        "/analisar/arquivo",
        files={"arquivo": ("foto.png", b"\x89PNG\r\n", "image/png")},
    )
    assert resposta.status_code == 400
    detalhe = resposta.json()["detail"]
    assert ".csv" in detalhe and ".pdf" in detalhe


def test_upload_com_colunas_erradas_diz_o_que_falta(cliente_com_sinal):
    resposta = cliente_com_sinal.post(
        "/analisar/arquivo",
        files={"arquivo": ("errado.csv", b"nome,idade\nana,30\n", "text/csv")},
    )
    assert resposta.status_code == 400
    assert "conversa_id" in resposta.json()["detail"]


def test_upload_vazio_e_400(cliente_com_sinal):
    resposta = cliente_com_sinal.post(
        "/analisar/arquivo",
        files={"arquivo": ("vazio.csv", b"", "text/csv")},
    )
    assert resposta.status_code == 400


def test_upload_acima_do_teto_e_recusado_antes_de_rodar_o_modelo(cliente_com_sinal):
    from fraus.api.main import TETO_ARQUIVO_ANALISE

    resposta = cliente_com_sinal.post(
        "/analisar/arquivo",
        files={"arquivo": ("grande.csv", b"x" * (TETO_ARQUIVO_ANALISE + 1), "text/csv")},
    )
    assert resposta.status_code == 400
    assert "limite" in resposta.json()["detail"]


def test_upload_acima_do_teto_nao_e_lido_por_inteiro(cliente_com_sinal, monkeypatch):
    """O teto tem que recusar SEM materializar o arquivo.

    Antes, a rota fazia `await arquivo.read()` (sem argumento) e so entao
    conferia o tamanho: o limite protegia a CPU do BERTimbau, que era a
    intencao declarada, e nunca a memoria -- o arquivo inteiro ja estava
    dentro dela quando a recusa acontecia. Este teste falha se alguem voltar a
    ler tudo de uma vez, porque a leitura sem tamanho reaparece no espiao.
    """
    # A classe espionada e a do STARLETTE, nao a reexportada pelo FastAPI: quem
    # instancia o upload e o parser do multipart, e ele constroi a do Starlette.
    # Espionar a subclasse do FastAPI nao intercepta chamada nenhuma -- foi o
    # primeiro jeito que tentei, e o teste passou por engano com zero leituras.
    from starlette.datastructures import UploadFile as UploadFileDoStarlette

    from fraus.api.rotas import analise

    tamanhos_pedidos = []
    leitura_original = UploadFileDoStarlette.read

    async def espiao(self, size=-1):
        tamanhos_pedidos.append(size)
        return await leitura_original(self, size)

    monkeypatch.setattr(UploadFileDoStarlette, "read", espiao)

    resposta = cliente_com_sinal.post(
        "/analisar/arquivo",
        files={"arquivo": ("grande.csv", b"x" * (analise.TETO_ARQUIVO_ANALISE + 1), "text/csv")},
    )

    assert resposta.status_code == 400
    # Nenhuma leitura ilimitada, e nenhum pedaco maior que o combinado.
    assert tamanhos_pedidos, "a rota nao leu o upload"
    assert all(0 < tamanho <= analise.PEDACO_DE_LEITURA for tamanho in tamanhos_pedidos)


def test_corpo_absurdo_e_413_antes_de_qualquer_parse(cliente_com_sinal):
    """A unica trava que age ANTES do multipart ser lido.

    Quando o handler de `/analisar/arquivo` comeca a rodar, o `UploadFile` ja
    foi resolvido -- o corpo ja foi lido e ja escorreu para um temporario em
    disco. Conferir tamanho la dentro nunca poderia evitar esse custo; so o
    middleware de `Content-Length` pode, e e ele que este teste cobre.
    """
    from fraus.api.main import TETO_CORPO

    resposta = cliente_com_sinal.post(
        "/analisar",
        content=b"x" * (TETO_CORPO + 1),
        headers={"content-type": "application/json"},
    )
    assert resposta.status_code == 413
    assert "limite" in resposta.json()["detail"]


def test_content_length_nao_numerico_e_recusado(cliente_com_sinal):
    """Deixar passar seria abrir a excecao exata que pula o teto."""
    resposta = cliente_com_sinal.post(
        "/analisar",
        content=b"{}",
        headers={"content-type": "application/json", "content-length": "abc"},
    )
    assert resposta.status_code == 400


def test_indicadores_trazem_o_intervalo_de_confianca_do_nps(cliente, tmp_path):
    """Uma conversa so: o intervalo existe, e o ponto estimado NAO aparece.

    n=1 esta muito abaixo de N_MINIMO_NPS, e o ponto com essa amostra
    sugeriria uma precisao que nao existe. A contagem vem preenchida para a
    tela dizer quanto falta.
    """
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    intervalo = cliente.get("/indicadores").json()["nps_intervalo"]
    assert intervalo["n"] == 1
    assert intervalo["nps"] is None
    assert intervalo["ic_inferior"] <= intervalo["ic_superior"]


def test_sem_score_nenhum_nao_ha_intervalo_de_nps(cliente):
    assert cliente.get("/indicadores").json()["nps_intervalo"] is None


def test_deriva_recusa_responder_com_motor_duble(cliente):
    """Diagnostico de deriva com motor dublê seria diagnostico inventado.

    A rota le `mean_`/`scale_` de um `StandardScaler` TREINADO. O dublê nao
    tem nenhum, e devolver um relatorio vazio dali se leria como "nenhuma
    feature fora da faixa" -- a mesma classe de defeito que fez a tela
    escrever "API no ar" durante um dia enquanto todo numero era sintetico.
    E a invariante 7 aplicada a um endpoint de diagnostico.
    """
    resposta = cliente.get("/saude/deriva")
    assert resposta.status_code == 503
    assert "dubl" in resposta.json()["detail"].lower()


def test_deriva_recusa_amostra_absurda(cliente):
    """O teto existe porque cada conversa da amostra custa uma passagem de BERTimbau."""
    assert cliente.get("/saude/deriva?n=100000").status_code == 400


def test_o_resumo_marca_evidencia_fraca_e_diz_por_que(cliente_com_sinal, tmp_path):
    """Duas falas de uma palavra: tem score, e nao ha material para sustenta-lo."""
    caminho = tmp_path / "curta.csv"
    caminho.write_text(
        "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
        "curta,csv,bot,ola posso ajudar,2026-08-13T10:00:00+00:00,false\n"
        "curta,csv,cliente,ok,2026-08-13T10:00:08+00:00,false\n"
        "curta,csv,cliente,valeu,2026-08-13T10:00:15+00:00,false\n",
        encoding="utf-8",
    )
    cliente_com_sinal.post("/conversas/importar", json={"caminho": str(caminho)})

    resumo = cliente_com_sinal.get("/conversas").json()[0]
    assert resumo["score"] is not None  # tem sinal: nao e o caso da cabeca vazada
    assert resumo["evidencia_fraca"] is True
    assert resumo["motivos_evidencia_fraca"] == ["menos de 5 palavras do cliente"]


def test_conversa_sem_fala_do_cliente_nao_e_evidencia_fraca_e_sim_ausencia(
    cliente_com_sinal, tmp_path
):
    """"Sem sinal" tem forma propria (a cabeca vazada) e nao vira tracejada."""
    caminho = tmp_path / "mudo.csv"
    caminho.write_text(CSV_SEM_CLIENTE, encoding="utf-8")
    cliente_com_sinal.post("/conversas/importar", json={"caminho": str(caminho)})

    resumo = cliente_com_sinal.get("/conversas").json()[0]
    assert resumo["score"] is None
    assert resumo["evidencia_fraca"] is None
