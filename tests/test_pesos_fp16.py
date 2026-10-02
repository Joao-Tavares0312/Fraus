import numpy as np
import pytest

onnx = pytest.importorskip("onnx", reason="onnx nao instalado (extra `conversao`)")
ort = pytest.importorskip("onnxruntime", reason="onnxruntime nao instalado (extra `onnx`)")

from onnx import TensorProto, helper, numpy_helper  # noqa: E402

from fraus.pesos_fp16 import guardar_em_fp16  # noqa: E402


def _grafo(caminho, pesos):
    grafo = helper.make_graph(
        [helper.make_node("MatMul", ["x", "w"], ["y"])],
        "g",
        [helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, pesos.shape[0]])],
        [helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, pesos.shape[1]])],
        [numpy_helper.from_array(pesos, "w"),
         numpy_helper.from_array(np.ones(3, dtype=np.float32), "pequeno")],
    )
    modelo = helper.make_model(grafo, opset_imports=[helper.make_opsetid("", 18)])
    modelo.ir_version = 10
    onnx.save(modelo, str(caminho))


def _rodar(caminho, x):
    sessao = ort.InferenceSession(str(caminho), providers=["CPUExecutionProvider"])
    return sessao.run(None, {"x": x})[0]


def test_pesos_em_fp16_no_disco_e_conta_em_fp32(tmp_path):
    # Pesos que ja cabem em float16, como os do checkpoint do Laya (gravado em half).
    pesos = np.random.default_rng(0).standard_normal((64, 32)).astype(np.float16).astype(np.float32)
    origem, destino = tmp_path / "a.onnx", tmp_path / "b.onnx"
    _grafo(origem, pesos)

    convertidos, perda = guardar_em_fp16(origem, destino)

    assert convertidos == 1          # o tensor pequeno fica como esta
    assert perda == 0.0              # float16 -> float32 -> float16 e exato
    assert destino.stat().st_size < origem.stat().st_size * 0.6
    x = np.random.default_rng(1).standard_normal((1, 64)).astype(np.float32)
    saida = _rodar(destino, x)
    assert saida.dtype == np.float32
    np.testing.assert_array_equal(saida, _rodar(origem, x))


def test_perda_e_reportada_quando_o_peso_nao_cabe_em_fp16(tmp_path):
    pesos = np.full((64, 32), 1.0 + 1e-6, dtype=np.float32)
    origem = tmp_path / "a.onnx"
    _grafo(origem, pesos)
    _, perda = guardar_em_fp16(origem, tmp_path / "b.onnx")
    assert perda > 0.0
