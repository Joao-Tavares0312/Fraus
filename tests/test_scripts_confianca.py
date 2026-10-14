"""Instrumentos de confianca: calibrar_conformal, medir_calibracao, medir_abstencao.

Fusor sintetico treinado em memoria (nunca os pesos reais) e holdout sintetico
pequeno em tmp_path, com classes SOBREPOSTAS para a cobertura ser informativa.
"""
import importlib.util
import json
import random
import sys
from pathlib import Path

import joblib
import pytest

from fraus.fusor import NOMES_FEATURES, Fusor

RAIZ = Path(__file__).resolve().parent.parent


def _script(nome):
    sys.path.insert(0, str(RAIZ / "scripts"))
    spec = importlib.util.spec_from_file_location(nome, RAIZ / "scripts" / f"{nome}.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _amostra(sorteio, rotulo):
    f = {n: 0.0 for n in NOMES_FEATURES}
    f["texto_prob_satisfeito_media"] = min(1, max(0, sorteio.gauss(0.25 + 0.25 * rotulo, 0.25)))
    f["texto_prob_insatisfeito_media"] = min(1, max(0, sorteio.gauss(0.75 - 0.25 * rotulo, 0.25)))
    f["latencia_mediana_s"] = max(1.0, sorteio.gauss(200 - 80 * rotulo, 120))
    f["qtd_turnos_cliente"] = float(sorteio.choice([1, 2, 3, 5]))
    f["emoji_contagem"] = float(sorteio.choice([0, 0, 1]))
    return f


def _lote(n_por_classe, semente):
    sorteio = random.Random(semente)
    xs, ys = [], []
    for _ in range(n_por_classe):
        for r in (0, 1, 2):
            xs.append(_amostra(sorteio, r))
            ys.append(r)
    return xs, ys


@pytest.fixture(scope="module")
def ambiente(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("conf")
    xt, yt = _lote(80, 1)
    fusor = Fusor()
    fusor.treinar(xt, yt)
    caminho_fusor = pasta / "fusor.joblib"
    joblib.dump(fusor._pipeline, caminho_fusor)
    xe, ye = _lote(100, 2)
    cache = pasta / "cache.json"
    cache.write_text(json.dumps({"xt": xt, "yt": yt, "xe": xe, "ye": ye}))
    return {"fusor": caminho_fusor, "cache": cache, "pasta": pasta}


def _preparar(ambiente):
    comum = sys.modules["_confianca_comum"]
    fusor = comum.carregar_fusor(ambiente["fusor"])
    xe, ye = comum.carregar_holdout(ambiente["cache"])
    return comum.preparar(fusor, xe, ye), ye


def test_cobertura_medida_fica_perto_do_alvo(ambiente):
    m = _script("calibrar_conformal")
    preparado, ye = _preparar(ambiente)
    limites, medida = m.calibrar(preparado, ye, 0.9)
    assert set(limites) == {0, 1, 2}
    # n por classe na avaliacao = 50: tolerancia binomial generosa
    assert medida["cobertura"] == pytest.approx(0.9, abs=0.1)
    assert medida["tamanho_medio"] > 0


def test_sem_gravar_nao_cria_arquivo(ambiente, capsys):
    m = _script("calibrar_conformal")
    saida = ambiente["pasta"] / "nao_deve_existir.json"
    assert m.main(["--cache", str(ambiente["cache"]), "--fusor", str(ambiente["fusor"]),
                   "--saida", str(saida)]) == 0
    assert not saida.exists()
    out = capsys.readouterr().out
    assert "tempo sintético" in out and "semente 20261014" in out


def test_gravar_escreve_artefato_com_a_regua(ambiente):
    m = _script("calibrar_conformal")
    saida = ambiente["pasta"] / "sub" / "conformal.json"
    assert m.main(["--cache", str(ambiente["cache"]), "--fusor", str(ambiente["fusor"]),
                   "--saida", str(saida), "--gravar"]) == 0
    artefato = json.loads(saida.read_text())
    assert set(artefato["limites"]) == {"0", "1", "2"}
    assert artefato["regua"] and artefato["alvo"] == 0.9


def test_fusor_ausente_falha_alto(ambiente):
    for nome in ("calibrar_conformal", "medir_calibracao", "medir_abstencao"):
        m = _script(nome)
        with pytest.raises(SystemExit) as erro:
            m.main(["--cache", str(ambiente["cache"]), "--fusor", str(ambiente["pasta"] / "nada.joblib")])
        assert erro.value.code not in (0, None)


def test_classe_sem_exemplo_na_calibracao_e_recusada(ambiente, tmp_path):
    m = _script("calibrar_conformal")
    xe, ye = _lote(100, 2)
    # classe 1 some do holdout
    pares = [(x, y) for x, y in zip(xe, ye) if y != 1]
    cache = tmp_path / "c.json"
    cache.write_text(json.dumps({"xe": [p[0] for p in pares], "ye": [p[1] for p in pares]}))
    saida = tmp_path / "s.json"
    with pytest.raises(SystemExit) as erro:
        m.main(["--cache", str(cache), "--fusor", str(ambiente["fusor"]), "--saida", str(saida), "--gravar"])
    assert erro.value.code not in (0, None)
    assert not saida.exists()


def test_abstencao_varre_os_alvos_e_marca_090(ambiente, capsys):
    m = _script("medir_abstencao")
    assert m.main(["--cache", str(ambiente["cache"]), "--fusor", str(ambiente["fusor"])]) == 0
    out = capsys.readouterr().out
    for alvo in ("0.80", "0.85", "0.90", "0.95"):
        assert alvo in out
    assert "ponto de operação" in out and "Risco x cobertura" in out
    preparado, ye = _preparar(ambiente)
    baixo, alto = m.medir_alvo(preparado, ye, 0.80), m.medir_alvo(preparado, ye, 0.95)
    assert alto["tamanho_medio"] >= baixo["tamanho_medio"]
    assert m.tolerancia_binomial(0.9, 150) == pytest.approx(2 * (0.9 * 0.1 / 150) ** 0.5)


def test_calibracao_imprime_tabelas_e_nao_grava(ambiente, capsys):
    m = _script("medir_calibracao")
    antes = set(ambiente["pasta"].iterdir())
    assert m.main(["--cache", str(ambiente["cache"]), "--fusor", str(ambiente["fusor"])]) == 0
    assert set(ambiente["pasta"].iterdir()) == antes
    out = capsys.readouterr().out
    for trecho in ("Metade de avaliação", "Holdout inteiro", "ece_classe_2", "Faixas", "Por fatia", "IC95%"):
        assert trecho in out


def test_temperatura_e_so_proposta():
    m = _script("medir_calibracao")
    # superconfiante e errada metade das vezes: T > 1 deve aparecer
    probs = [[0.02, 0.02, 0.96]] * 100
    rotulos = [2] * 50 + [0] * 50
    t = m.ajustar_temperatura(probs, rotulos)
    assert t > 1.5
    assert m.temperar(probs, 1.0)[0] == pytest.approx(probs[0], abs=1e-9)
    assert "não aplicada" in m.AVISO_TEMPERATURA


def test_png_sem_matplotlib_da_mensagem_clara(ambiente, tmp_path, monkeypatch):
    m = _script("medir_calibracao")
    monkeypatch.setitem(sys.modules, "matplotlib", None)
    with pytest.raises(SystemExit) as erro:
        m.reliability_png([[0.1, 0.2, 0.7]] * 5, [2] * 5, tmp_path / "r.png")
    assert "uv run --with matplotlib" in str(erro.value)


# ---- rodada de correcao 1 ----

def _conversa(falas, escalou=False):
    from datetime import datetime, timedelta, timezone
    from fraus.modelos import Conversa, Mensagem
    base = datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)
    return Conversa(id="x", canal="csv", iniciada_em=base, escalou_para_humano=escalou, mensagens=[
        Mensagem(autor=a, texto=t, enviada_em=base + timedelta(seconds=s)) for a, t, s in falas])


def test_fatias_das_features_batem_com_fatias_de():
    from fraus.fatias import fatias_de
    from fraus.fusor import montar_features
    from tests.test_motor import _EmocaoDuble, _TextoDuble
    m = _script("medir_calibracao")
    casos = [
        _conversa([("cliente", "oi", 0)]),  # sem resposta: sem medida
        _conversa([("cliente", "oi \U0001F600", 0), ("bot", "ola", 10)]),  # emoji
        _conversa([("cliente", "oi", 0), ("bot", "ola", 500)], escalou=True),
        _conversa([("cliente", "oi", 0), ("bot", "ola", 100), ("cliente", "a", 110), ("bot", "b", 150)]),
        _conversa([("cliente", "oi", 0), ("bot", "a", 5)] + [x for k in range(4) for x in
                   (("cliente", "c", 10 + 20 * k), ("bot", "r", 15 + 20 * k))]),  # 5 falas
    ]
    for c in casos:
        f = montar_features(c, _TextoDuble(), _EmocaoDuble())
        assert m.fatias_das_features(f) == fatias_de(c)


def test_classe_ausente_nao_vira_ece_zero(ambiente, tmp_path, capsys):
    m = _script("medir_calibracao")
    xe, ye = _lote(100, 2)
    pares = [(x, y) for x, y in zip(xe, ye) if y != 1]
    cache = tmp_path / "c.json"
    cache.write_text(json.dumps({"xe": [p[0] for p in pares], "ye": [p[1] for p in pares]}))
    with pytest.raises(SystemExit) as erro:
        m.main(["--cache", str(cache), "--fusor", str(ambiente["fusor"])])
    assert erro.value.code not in (0, None)


def test_ic_vem_com_mediana_e_aviso_de_vies(ambiente, capsys):
    m = _script("medir_calibracao")
    assert m.main(["--cache", str(ambiente["cache"]), "--fusor", str(ambiente["fusor"])]) == 0
    out = capsys.readouterr().out
    assert "mediana bootstrap" in out
    assert "ECE binado é enviesado para cima em amostra pequena; o IC percentil pode não conter a estimativa" in out


# ---- rodada de correcao 2 ----

def test_classe_rara_nao_derruba_o_bootstrap_nem_vira_zero():
    m = _script("medir_calibracao")
    probs = [[0.7, 0.2, 0.1]] * 60 + [[0.2, 0.6, 0.2]] * 40 + [[0.1, 0.2, 0.7]] * 2
    rotulos = [0] * 60 + [1] * 40 + [2] * 2
    saida = m.medir(probs, rotulos, reamostras=200)
    ic = saida["ece_classe_2"][1]
    assert ic is None or all(v > 0 for v in ic)  # indisponivel, nunca "[0, 0]"
    from io import StringIO
    import contextlib
    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        m._imprimir_medidas("x", probs, rotulos)
    assert "0.0000  IC95% [0.0000, 0.0000]" not in buf.getvalue()


def test_guarda_exige_minimo_e_nomeia_a_metade():
    comum = sys.modules.get("_confianca_comum") or _script("medir_calibracao") and sys.modules["_confianca_comum"]
    grupos = {0: [1] * 10, 1: [1] * 10, 2: [1, 2]}
    with pytest.raises(SystemExit) as erro:
        comum.exigir_todas_as_classes(grupos, metade="avaliação")
    msg = str(erro.value)
    assert "metade de avaliação" in msg and "2" in msg and "calibração" not in msg


# ---- rodada final do E2 ----

def test_png_cria_pasta_pai(tmp_path):
    pytest.importorskip("matplotlib")
    m = _script("medir_calibracao")
    destino = tmp_path / "a" / "b" / "r.png"
    m.reliability_png([[0.1, 0.2, 0.7]] * 5, [2] * 5, destino)
    assert destino.exists()


def test_ece_por_fatia_com_n_pequeno_e_nd(ambiente, capsys):
    m = _script("medir_calibracao")
    assert m.main(["--cache", str(ambiente["cache"]), "--fusor", str(ambiente["fusor"])]) == 0
    out = capsys.readouterr().out
    trecho = out.split("Por fatia (avaliação)")[1]
    assert "ECE" in trecho
    linhas = [l for l in trecho.splitlines() if "n=" in l]
    assert linhas and all("ECE " in l for l in linhas)


def test_ece_da_fatia_nd_abaixo_de_5_e_nunca_zero():
    m = _script("medir_calibracao")
    assert m.texto_ece([[0.1, 0.2, 0.7]] * 4, [2] * 4) == "n/d"
    assert m.texto_ece([[0.1, 0.2, 0.7]] * 5, [2] * 5) != "n/d"
