"""Corpus sintético selado: dados válidos, reprodução e contenção de escrita."""
from collections import Counter, defaultdict
from datetime import timedelta
import hashlib
import importlib
import json
from pathlib import Path

import pytest

from fraus.ingest.simulador import FRASES_POR_ROTULO, gerar_lote
from fraus.modelos import Conversa


@pytest.fixture
def ouro():
    return importlib.import_module("scripts.analise_motores.ouro")


def _executar(ouro, workspace, saida):
    return ouro.main(["--workspace", str(workspace), "--saida", str(saida)])


def _ler(saida):
    dados = (saida / "conversas.jsonl").read_bytes()
    return [json.loads(linha) for linha in dados.splitlines()]


def test_exatamente_120_do_simulador_e_80_em_oito_grupos(ouro):
    registros = ouro.gerar_registros()
    assert len(registros) == 200
    assert len({r["id"] for r in registros}) == 200
    assert all(set(r) == {"id", "grupo", "par_id", "rotulo_sintetico", "conversa"} for r in registros)
    simulados = [r for r in registros if r["grupo"] == "simulador"]
    esperado = gerar_lote(FRASES_POR_ROTULO, quantidade=120, semente=20261016)
    assert [(r["conversa"], r["rotulo_sintetico"]) for r in simulados] == [
        (c.model_dump(mode="json"), rotulo) for c, rotulo in esperado
    ]
    assert Counter(r["rotulo_sintetico"] for r in simulados) == {0: 40, 1: 40, 2: 40}
    assert Counter(r["grupo"] for r in registros if r["grupo"] != "simulador") == {
        "sem_cliente": 10, "cliente_vazio": 10, "cortesia": 10,
        "valencia_negacao": 10, "ironia": 10, "emoji": 10,
        "estilo": 10, "estrutura_tempo_longo": 10,
    }


def test_todas_conversas_validas_nao_vazias_e_timestamps_aware(ouro):
    for registro in ouro.gerar_registros():
        conversa = Conversa.model_validate(registro["conversa"])
        assert conversa.id == registro["id"]
        assert conversa.mensagens
        datas = [conversa.iniciada_em, *(m.enviada_em for m in conversa.mensagens)]
        if conversa.encerrada_em is not None:
            datas.append(conversa.encerrada_em)
        assert all(d.utcoffset() is not None for d in datas)
        assert datas[1:1 + len(conversa.mensagens)] == sorted(m.enviada_em for m in conversa.mensagens)
        assert all(m.enviada_em >= conversa.iniciada_em for m in conversa.mensagens)
        assert conversa.encerrada_em is None or conversa.encerrada_em >= conversa.mensagens[-1].enviada_em


def test_pares_dirigidos_tem_duas_variantes_e_ids_estaveis(ouro):
    pares = defaultdict(list)
    registros = ouro.gerar_registros()
    assert registros == ouro.gerar_registros()
    for registro in registros:
        if registro["grupo"] == "simulador":
            assert registro["par_id"] is None
        else:
            assert registro["par_id"]
            pares[registro["par_id"]].append(registro)
    assert len(pares) == 40
    assert all(len(p) == 2 and len({r["grupo"] for r in p}) == 1 for p in pares.values())
    assert all(p[0]["conversa"] != p[1]["conversa"] for p in pares.values())


def test_casos_de_fronteira_sao_explicitos_e_sem_falso_ground_truth(ouro):
    registros = ouro.gerar_registros()
    por_grupo = defaultdict(list)
    for registro in registros:
        por_grupo[registro["grupo"]].append(Conversa.model_validate(registro["conversa"]))
    assert all(not c.mensagens_cliente and not c.tem_sinal_cliente for c in por_grupo["sem_cliente"])
    assert all(c.mensagens_cliente and not c.tem_sinal_cliente for c in por_grupo["cliente_vazio"])
    assert all(c.motivo_sem_sinal == "so_cortesia" for c in por_grupo["cortesia"])
    textos = [m.texto for r in registros for m in Conversa.model_validate(r["conversa"]).mensagens_cliente]
    assert "vlw" in textos and "blz" in textos
    assert "que atendimento maravilhoso, so esperei 3 horas" in textos
    assert any("\u200d" in t and "👩" in t for t in textos)
    assert any("\u0301" in t for t in textos)
    assert any(len(t.split()) > 192 for t in textos)
    assert any(
        any((b.enviada_em - a.enviada_em) >= timedelta(days=30) for a, b in zip(c.mensagens, c.mensagens[1:]))
        for c in por_grupo["estrutura_tempo_longo"]
    )
    assert all(r["rotulo_sintetico"] is None for r in registros if r["grupo"] in {"sem_cliente", "cliente_vazio", "cortesia"})
    assert all(r["rotulo_sintetico"] in (None, 0, 1, 2) for r in registros)


def test_geracao_tem_bytes_identicos_e_manifesto_confere_o_conteudo(ouro, tmp_path):
    workspace = tmp_path / "workspace"
    a, b = workspace / "a", workspace / "b"
    assert _executar(ouro, workspace, a) == 0
    assert _executar(ouro, workspace, b) == 0
    for nome in ("conversas.jsonl", "manifesto.json"):
        assert (a / nome).read_bytes() == (b / nome).read_bytes()
    manifesto = json.loads((a / "manifesto.json").read_text())
    assert manifesto["semente"] == 20261016
    assert manifesto["quantidade"] == 200
    assert manifesto["sha256_conversas"] == hashlib.sha256((a / "conversas.jsonl").read_bytes()).hexdigest()
    assert manifesto["rotulos_sao_ground_truth"] is False
    assert manifesto["uso_rotulos"]
    expectativas = manifesto["expectativas"]
    registros = _ler(a)
    assert set(expectativas) == {r["id"] for r in registros}
    for r in registros:
        c = Conversa.model_validate(r["conversa"])
        assert expectativas[r["id"]] == {
            "tem_sinal_cliente": c.tem_sinal_cliente,
            "motivo_sem_sinal": c.motivo_sem_sinal,
            "score_nota_categoria_nulos": not c.tem_sinal_cliente,
        }
    resultado = json.loads((workspace / "experimentos/resultados/ouro.json").read_text())
    assert resultado["fase"] == "ouro" and resultado["status"] == "medido"
    assert resultado["condicoes"]["n"] == 200
    assert resultado["condicoes"]["hashes"]["conversas.jsonl"] == manifesto["sha256_conversas"]


def test_destino_externo_ao_workspace_e_recusado_sem_escrita(ouro, tmp_path):
    workspace, externo = tmp_path / "workspace", tmp_path / "proibido"
    assert _executar(ouro, workspace, externo) == 2
    assert not externo.exists()
    resultado = json.loads((workspace / "experimentos/resultados/ouro.json").read_text())
    assert resultado["status"] == "nao_verificado" and resultado["motivo"]


def test_destino_versionado_exato_e_autorizado_mas_subpasta_nao(ouro, tmp_path, monkeypatch):
    raiz = tmp_path / "repo"
    raiz.mkdir()
    monkeypatch.setattr(ouro, "RAIZ", raiz)
    autorizado = raiz / "tests/golden/analise_motores"
    workspace = tmp_path / "workspace"
    assert _executar(ouro, workspace, autorizado / "intruso") == 2
    assert not autorizado.exists()
    assert _executar(ouro, workspace, autorizado) == 0
    assert len(_ler(autorizado)) == 200


@pytest.mark.parametrize("tipo", ["destino", "ancestral", "conversas", "manifesto", "workspace"])
def test_symlinks_sao_recusados_sem_tocar_no_alvo(ouro, tmp_path, tipo):
    workspace, alvo = tmp_path / "workspace", tmp_path / "original"
    alvo.mkdir()
    marcador = alvo / "intacto"
    marcador.write_bytes(b"nao alterar")
    saida = workspace / "ouro"
    if tipo == "workspace":
        workspace.symlink_to(alvo, target_is_directory=True)
    else:
        workspace.mkdir()
        if tipo == "destino":
            saida.symlink_to(alvo, target_is_directory=True)
        elif tipo == "ancestral":
            (workspace / "atalho").symlink_to(alvo, target_is_directory=True)
            saida = workspace / "atalho/ouro"
        else:
            saida.mkdir()
            nome = "conversas.jsonl" if tipo == "conversas" else "manifesto.json"
            (saida / nome).symlink_to(marcador)
    antes = {p.relative_to(alvo): p.read_bytes() for p in alvo.rglob("*") if p.is_file()}
    assert _executar(ouro, workspace, saida) == 2
    assert {p.relative_to(alvo): p.read_bytes() for p in alvo.rglob("*") if p.is_file()} == antes


def test_recusa_nao_expoe_caminho_arbitrario(ouro, tmp_path, capsys):
    segredo = "TOKEN_EXEMPLO_NAO_IMPRIMIR"
    workspace = tmp_path / "workspace"
    assert _executar(ouro, workspace, tmp_path / segredo) == 2
    saida = capsys.readouterr()
    assert segredo not in saida.out + saida.err
    assert segredo not in (workspace / "experimentos/resultados/ouro.json").read_text()
