"""Pesos de um grafo ONNX gravados em float16 e convertidos para float32 na carga.

O checkpoint do Laya ja e gravado em meia precisao (`model.safetensors` em
half); o export para ONNX so o reescreve em float32, dobrando o arquivo sem
acrescentar informacao. Aqui os pesos voltam a float16 NO DISCO e um no `Cast`
os devolve a float32 quando o grafo e carregado: a conta roda nos mesmos
numeros e no mesmo tipo de antes, e o arquivo cai pela metade.

Nao e quantizacao. INT8 dinamico no encoder do Laya troca decisoes (medido em
02/10/2026: 71% delas no checkpoint de fumaca); isto nao troca nenhuma, e
`guardar_em_fp16` devolve a maior diferenca de peso para quem chama conferir.

`onnx` so e importado aqui dentro: o modulo e ferramenta de conversao, nunca
de deploy.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def guardar_em_fp16(origem: Path | str, destino: Path | str, *, minimo: int = 1024) -> tuple[int, float]:
    """Grava `destino` com os tensores float32 grandes em float16.

    Devolve `(tensores_convertidos, maior_diferenca_de_peso)`. Diferenca zero
    quer dizer que os pesos ja cabiam em float16 e nada foi arredondado.
    Tensores com menos de `minimo` elementos ficam como estao.
    """
    import onnx
    from onnx import TensorProto, helper, numpy_helper

    modelo = onnx.load(str(origem))
    conversoes, perda = [], 0.0
    for indice, tensor in enumerate(list(modelo.graph.initializer)):
        if tensor.data_type != TensorProto.FLOAT or int(np.prod(tensor.dims)) < minimo:
            continue
        original = numpy_helper.to_array(tensor)
        meio = original.astype(np.float16)
        perda = max(perda, float(np.abs(meio.astype(np.float32) - original).max()))
        modelo.graph.initializer.remove(tensor)
        modelo.graph.initializer.append(numpy_helper.from_array(meio, f"{tensor.name}__fp16"))
        conversoes.append(
            helper.make_node(
                "Cast", [f"{tensor.name}__fp16"], [tensor.name],
                to=TensorProto.FLOAT, name=f"fp16_para_fp32_{indice}",
            )
        )
    # As conversoes vem antes de qualquer no que use o peso.
    nos = conversoes + list(modelo.graph.node)
    del modelo.graph.node[:]
    modelo.graph.node.extend(nos)
    del modelo.graph.value_info[:]
    onnx.save(modelo, str(destino))
    return len(conversoes), perda
