import importlib.util
from pathlib import Path

from fraus.dados.casos_sinalizadores import CASOS
from fraus.sinalizadores import REGRAS, sinalizadores

_spec = importlib.util.spec_from_file_location(
    "medir_sinalizadores", Path(__file__).parent.parent / "scripts" / "medir_sinalizadores.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
carregar_anotada, medir, principal = _mod.carregar_anotada, _mod.medir, _mod.principal


def test_tres_casos_por_regra_um_de_cada_tipo():
    for regra in REGRAS:
        tipos = sorted(t for r, t, _, _ in CASOS if r == regra)
        assert tipos == ["borda", "negativo", "positivo"], regra


def test_cada_caso_construido_se_comporta_como_declarado():
    for regra, tipo, conversa, deve in CASOS:
        disparou = regra in [s["regra"] for s in sinalizadores(conversa) or []]
        assert disparou == deve, (regra, tipo)


def test_medir_denominador_zero_e_none_e_nao_zero():
    res = medir([(r, t, c, d) for r, t, c, d in CASOS if not d])
    assert res["loop_do_bot"]["precisao"] is None
    assert res["loop_do_bot"]["ic_precisao"] is None


def test_medir_nos_casos_construidos():
    res = medir(CASOS)
    for regra in REGRAS:
        assert res[regra]["fn"] == 0 and res[regra]["fp"] == 0
        assert res[regra]["vp"] > 0


def test_saida_declara_o_que_mede_e_o_que_falta(capsys):
    principal([])
    saida = capsys.readouterr().out
    assert "verifica a implementação, não mede qualidade" in saida
    assert "não verificado" in saida and "fonte pendente" in saida


def test_anotada_le_jsonl(tmp_path):
    import json
    conversa = CASOS[0][2]
    arq = tmp_path / "a.jsonl"
    arq.write_text(json.dumps({"conversa": conversa.model_dump(mode="json"),
                               "esperadas": ["loop_do_bot"], "anotador": "teste"}) + "\n")
    casos, anotadores = carregar_anotada(arq)
    assert anotadores == {"teste"}
    assert {(r, d) for r, _, _, d in casos if r == "loop_do_bot"} == {("loop_do_bot", True)}


def _linha(**sobre):
    import json
    item = {"conversa": CASOS[0][2].model_dump(mode="json"),
            "esperadas": ["loop_do_bot"], "anotador": "teste"}
    item.update(sobre)
    return json.dumps(item) + "\n"


def test_anotada_regra_desconhecida_e_erro_com_linha(tmp_path):
    import pytest
    arq = tmp_path / "a.jsonl"
    arq.write_text(_linha() + _linha(esperadas=["inventada"]))
    with pytest.raises(ValueError, match=r"inventada.*2|2.*inventada"):
        carregar_anotada(arq)


def test_anotada_sem_anotador_e_erro_com_linha(tmp_path):
    import json
    import pytest
    item = json.loads(_linha())
    del item["anotador"]
    arq = tmp_path / "a.jsonl"
    arq.write_text(json.dumps(item) + "\n")
    with pytest.raises(ValueError, match="1"):
        carregar_anotada(arq)


def test_anotada_vazia_e_erro(tmp_path):
    import pytest
    arq = tmp_path / "a.jsonl"
    arq.write_text("\n\n")
    with pytest.raises(ValueError, match="amostra anotada vazia"):
        carregar_anotada(arq)


def test_tabela_marca_construidos_nas_colunas(capsys):
    principal([])
    assert "precisão (construídos)" in capsys.readouterr().out
