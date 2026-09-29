"""Compatibilidade mínima do runtime ONNX da Laya, sem importar PyTorch."""

from __future__ import annotations

import json
import math
import sys
import threading
import types

import numpy as np

QTYPES = {"choice": 0, "score": 1, "noul": 2}
QTYPE_NAMES = {valor: nome for nome, valor in QTYPES.items()}
TEMP_MIN, TEMP_MAX = 0.5, 5.0
_TRAVA = threading.RLock()


class ArrayNumpy(np.ndarray):
    def numpy(self):
        return np.asarray(self)


def _array(valor, dtype):
    return np.asarray(valor, dtype=dtype).view(ArrayNumpy)


def encode_text(tokenizador, texto, **opcoes):
    with _TRAVA:
        return tokenizador(texto, **opcoes)


def serialize_state(estado):
    return estado if isinstance(estado, str) else json.dumps(estado, ensure_ascii=False)


def render_options(pergunta):
    criterios = pergunta.get("crit") or {}
    if pergunta["t"] != "choice":
        raise ValueError("o adaptador Fraus da Laya aceita perguntas choice")
    return [str(k) if v in (None, "") else f"{k}: {v}" for k, v in criterios.items()]


def build_sequence(tokenizador, estado, pergunta, max_len=512, head_max_len=192,
                   option_order=None, truncate_left=False, state_ids=None,
                   return_stats=False):
    mascara = tokenizador.mask_token
    opcoes = render_options(pergunta)
    ordem = option_order if option_order is not None else range(len(opcoes))
    instrucao = str(pergunta["ins"]).replace(mascara, " ")
    cabeca = encode_text(tokenizador, f"{pergunta['t']} question: {instrucao}",
                         add_special_tokens=False)["input_ids"]
    ids_opcoes = []
    for indice in ordem:
        tokens = encode_text(tokenizador, " " + opcoes[indice].replace(mascara, " "),
                             add_special_tokens=False, truncation=True,
                             max_length=48)["input_ids"]
        ids_opcoes.append([tokenizador.mask_token_id] + list(tokens))
    orcamento = head_max_len - sum(map(len, ids_opcoes))
    por_opcao = None
    if orcamento < 16:
        por_opcao = max(4, (head_max_len - 16) // max(1, len(ids_opcoes)))
        ids_opcoes = [item[:por_opcao] for item in ids_opcoes]
        orcamento = head_max_len - sum(map(len, ids_opcoes))
    ids = [tokenizador.cls_token_id] + list(cabeca[:max(8, orcamento)]) + [tokenizador.sep_token_id]
    marcadores = []
    for opcao in ids_opcoes:
        marcadores.append(len(ids)); ids.extend(opcao)
    ids.append(tokenizador.sep_token_id)
    espaco = max(0, max_len - len(ids) - 1)
    if state_ids is None:
        state_ids = encode_text(tokenizador, serialize_state(estado).replace(mascara, " "),
                                add_special_tokens=False)["input_ids"]
    trecho = state_ids[max(0, len(state_ids) - espaco):] if truncate_left else state_ids[:espaco]
    ids = (ids + list(trecho) + [tokenizador.sep_token_id])[:max_len]
    marcadores = [m for m in marcadores if m < max_len]
    if not return_stats:
        return ids, marcadores
    return ids, marcadores, {"options": len(ids_opcoes),
                              "options_distinct": len({tuple(o) for o in ids_opcoes}),
                              "tokens_per_option": por_opcao}


def collapsed_options(qids, itens):
    saida = {}
    for qid, item in zip(qids, itens):
        dados = item.get("options")
        if dados and dados["options_distinct"] < dados["options"]:
            saida[qid] = {"total": dados["options"], "distinct": dados["options_distinct"],
                          "tokens_per_option": dados["tokens_per_option"]}
    return saida


def answer_confidence(p, k):
    return float(np.clip(np.max(p[:k]), 0.0, 1.0)) if k else 1.0


def confidence_from_probs(p, k):
    if k < 2: return 1.0
    p = p[:k]
    return float(np.clip(1.0 + (p * np.log(np.clip(p, 1e-12, 1.0))).sum() / math.log(k), 0, 1))


def temp_bucket(qtype, k):
    tamanho = "2" if k <= 2 else "3-5" if k <= 5 else "6-10" if k <= 10 else "11+"
    return f"{QTYPE_NAMES[int(qtype)]}:{tamanho}"


def clamp_temperature(valor, lo=TEMP_MIN, hi=TEMP_MAX):
    try: valor = float(valor)
    except (TypeError, ValueError): return 1.0
    return 1.0 if not np.isfinite(valor) else min(hi, max(lo, valor))


def collate_items(lotes, pad_id):
    itens = [item for lote in lotes for item in lote]
    n, comprimento = len(itens), max(len(i["ids"]) for i in itens)
    max_marcadores = max(len(i["markers"]) for i in itens)
    ids = np.full((n, comprimento), pad_id, dtype=np.int64)
    atencao = np.zeros((n, comprimento), dtype=np.int64)
    posicoes = np.zeros((n, max_marcadores), dtype=np.int64)
    mascara = np.zeros((n, max_marcadores), dtype=bool)
    for indice, item in enumerate(itens):
        ids[indice, :len(item["ids"])] = item["ids"]
        atencao[indice, :len(item["ids"])] = 1
        posicoes[indice, :len(item["markers"])] = item["markers"]
        mascara[indice, :len(item["markers"])] = True
    return {"input_ids": ids.view(ArrayNumpy), "attention_mask": atencao.view(ArrayNumpy),
            "marker_pos": posicoes.view(ArrayNumpy), "marker_mask": mascara.view(ArrayNumpy),
            "qtype": _array([i["qtype"] for i in itens], np.int64)}


def instalar(corrigir_tokenizador):
    comum = types.ModuleType("laya.common")
    for nome in ("QTYPES", "answer_confidence", "build_sequence", "collapsed_options",
                 "collate_items", "confidence_from_probs", "encode_text", "render_options",
                 "serialize_state", "temp_bucket", "TEMP_MIN", "TEMP_MAX", "clamp_temperature"):
        setattr(comum, nome, globals()[nome])
    agente = types.ModuleType("laya.agent")
    agente._fix_tokenizer_config = corrigir_tokenizador
    class Agent:
        @staticmethod
        def _check_question(qid, pergunta):
            if pergunta.get("type") != "choice" or not isinstance(pergunta.get("criteria"), dict):
                raise ValueError(f"pergunta {qid!r} precisa ser choice com criteria")
    agente.Agent = Agent
    sys.modules["laya.common"] = comum
    sys.modules["laya.agent"] = agente
