import json
from pathlib import Path

import pytest

from fraus.avaliacao_ironia import (CAMINHO_META_REGUA, CAMINHO_REGUA_PARES, FraseDaRegua,
                                    carregar_regua_pares, impressao_dos_rotulos,
                                    variantes_de_invariancia)
from fraus.divisao import impressao_dos_textos


def _gravar(tmp_path: Path, textos):
    regua = tmp_path / "regua.csv"
    linhas = ["par_id,estrato,texto,rotulo,concordancia"]
    linhas += [f"p{i // 2},elogio,{t},{i % 2},1.0" for i, t in enumerate(textos)]
    regua.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    meta = tmp_path / "meta.json"
    impressao_rotulos = impressao_dos_rotulos((f"p{i // 2}", i % 2, t) for i, t in enumerate(textos))
    meta.write_text(
        json.dumps({"impressao": impressao_dos_textos(textos), "impressao_rotulos": impressao_rotulos}),
        encoding="utf-8",
    )
    return regua, meta


def test_carga_le_a_regua_congelada(tmp_path):
    regua, meta = _gravar(tmp_path, ["a", "b", "c", "d"])
    frases = carregar_regua_pares(regua, meta)
    assert frases[1] == FraseDaRegua("p0", "elogio", "b", 1, 1.0)


def test_carga_recusa_regua_editada(tmp_path):
    regua, meta = _gravar(tmp_path, ["a", "b", "c", "d"])
    regua.write_text(regua.read_text(encoding="utf-8").replace(",c,", ",C,"), encoding="utf-8")
    with pytest.raises(ValueError, match="impressao"):
        carregar_regua_pares(regua, meta)


def test_carga_recusa_rotulo_trocado_ou_par_movido(tmp_path):
    regua, meta = _gravar(tmp_path, ["a", "b", "c", "d"])
    original = regua.read_text(encoding="utf-8")
    regua.write_text(original.replace("p0,elogio,b,1,", "p0,elogio,b,0,"), encoding="utf-8")
    with pytest.raises(ValueError, match="rotulo"):
        carregar_regua_pares(regua, meta)
    regua.write_text(original.replace("p1,elogio,c,", "p0,elogio,c,"), encoding="utf-8")
    with pytest.raises(ValueError, match="rotulo"):
        carregar_regua_pares(regua, meta)


def test_invariancia_preserva_rotulo_e_muda_so_a_superficie():
    textos = [f"frase {i}." if i % 3 else f"frase {i}!" for i in range(30)]
    textos += ["quer mesmo isso? 🙂", "ja resolvi 🙂 🙂", "acabou a internet!"]
    frases = [FraseDaRegua(f"p{i}", "elogio", t, i % 2, 1.0) for i, t in enumerate(textos)]
    variantes = variantes_de_invariancia(frases, quantas=20)
    assert len(variantes) == 40
    origem = {f.texto: f for f in frases}
    assert variantes == variantes_de_invariancia(frases, quantas=20)
    for v in variantes:
        assert v["rotulo"] == origem[v["frase_origem"]].rotulo
        assert v["texto"] != v["frase_origem"]
        assert not v["texto"].endswith(("!.", "?."))
        assert "🙂 🙂" not in v["texto"]
        assert "🙂" not in v["frase_origem"]
        assert v["frase_origem"].rstrip()[-1].isalpha() or v["frase_origem"].rstrip().endswith(".")


def test_regua_versionada_bate_com_o_meta():
    if not CAMINHO_REGUA_PARES.exists():
        pytest.skip("regua de pares ainda nao anotada e congelada")
    assert carregar_regua_pares()  # levanta se a impressao nao bate
