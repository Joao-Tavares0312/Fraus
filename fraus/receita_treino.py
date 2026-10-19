"""A receita de treino comum aos notebooks 01 (satisfacao), 03 (emocao) e 04 (ironia).

Ate 19/10/2026 os tres notebooks passavam `eval_dataset=divisao['test']` com
`load_best_model_at_end=True`: a melhor epoca era escolhida NO TESTE, e o
numero reportado era um segundo `evaluate()` nesse mesmo teste. Nao havia
validacao. Os 0,782 da satisfacao e os 0,584 da emocao sao, por isso,
otimistas por construcao.

A regra daqui em diante:

- duplicata por texto normalizado sai ANTES de dividir (o GoEmotions-PT tem a
  mesma frase curta com ids diferentes, que caiam dos dois lados);
- tres lados: treino, validacao (escolhe epoca e temperatura) e teste (tocado
  uma vez, no fim);
- tres sementes, media e desvio reportados, e a semente MEDIANA promovida --
  promover a melhor de tres e escolher pelo acaso;
- a temperatura e ajustada na validacao e gravada no artefato.

Parte pura: numpy e, dentro de `dividir_treino_val_teste`, sklearn. Nada de
torch aqui -- o notebook monta o `Trainer` com o que estas funcoes devolvem.
"""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from fraus.calibracao import ece as ece_multiclasse
from fraus.comparacao_modelos import contagens_por_classe, f1_macro, matriz_de_confusao
from fraus.divisao import conferir_divisao, grupos_por_autor


# --- duplicatas ---------------------------------------------------------------


def normalizar_texto(texto: object) -> str:
    """Chave de duplicata: NFC, caixa ignorada, espacos colapsados."""
    return " ".join(unicodedata.normalize("NFC", str(texto)).casefold().split())


@dataclass(frozen=True)
class ResultadoDuplicatas:
    indices: list[int]
    duplicatas: int
    conflitos: int


def remover_duplicatas(textos: Sequence[object], rotulos: Sequence[int]) -> ResultadoDuplicatas:
    """Posicoes que sobrevivem; texto repetido fica so na primeira aparicao.

    Texto repetido com rotulos DIFERENTES sai inteiro (todas as aparicoes):
    nao ha resposta certa para treinar nem para medir.
    """
    if len(textos) != len(rotulos):
        raise ValueError("textos e rotulos de tamanhos diferentes")
    rotulos_por_chave: dict[str, set[int]] = {}
    for texto, rotulo in zip(textos, rotulos):
        rotulos_por_chave.setdefault(normalizar_texto(texto), set()).add(int(rotulo))
    vistos: set[str] = set()
    indices, duplicatas, conflitos = [], 0, 0
    for posicao, texto in enumerate(textos):
        chave = normalizar_texto(texto)
        if len(rotulos_por_chave[chave]) > 1:
            conflitos += 1
        elif chave in vistos:
            duplicatas += 1
        else:
            vistos.add(chave)
            indices.append(posicao)
    return ResultadoDuplicatas(indices, duplicatas, conflitos)


# --- divisao em tres --------------------------------------------------------


@dataclass(frozen=True)
class DivisaoTresLados:
    treino: list[int]
    validacao: list[int]
    teste: list[int]


def _separar(rotulos, posicoes, grupos, fracao, semente):
    """Divide `posicoes` em (resto, separado), por grupo ou estratificado."""
    from sklearn.model_selection import GroupShuffleSplit, train_test_split

    sub_rotulos = [rotulos[i] for i in posicoes]
    if grupos is None:
        resto, separado = train_test_split(
            list(range(len(posicoes))), test_size=fracao, random_state=semente,
            stratify=sub_rotulos,
        )
    else:
        sub_grupos = [grupos[i] for i in posicoes]
        divisor = GroupShuffleSplit(n_splits=1, test_size=fracao, random_state=semente)
        resto, separado = next(divisor.split(sub_grupos, groups=sub_grupos))
    resto = sorted(posicoes[int(i)] for i in resto)
    separado = sorted(posicoes[int(i)] for i in separado)
    conferir_divisao(
        [rotulos[i] for i in resto], [rotulos[i] for i in separado], fracao_teste=fracao
    )
    return resto, separado


def dividir_treino_val_teste(
    rotulos: Sequence[int],
    *,
    grupos: Sequence[object] | None = None,
    fracao_val: float = 0.10,
    fracao_teste: float = 0.15,
    semente: int = 42,
) -> DivisaoTresLados:
    """Treino, validacao e teste disjuntos, conferidos por `conferir_divisao`.

    Com `grupos` (autor, produto, fonte), nenhum grupo aparece em dois lados;
    grupo grande demais faz a conferencia levantar `ValueError`, nunca um teste
    de outro tamanho em silencio. Sem `grupos`, a divisao e estratificada.
    """
    rotulos = [int(r) for r in rotulos]
    if grupos is not None:
        if len(grupos) != len(rotulos):
            raise ValueError("grupos e rotulos de tamanhos diferentes")
        grupos = grupos_por_autor(grupos)
    todas = list(range(len(rotulos)))
    resto, teste = _separar(rotulos, todas, grupos, fracao_teste, semente)
    treino, validacao = _separar(
        rotulos, resto, grupos, fracao_val / (1.0 - fracao_teste), semente
    )
    return DivisaoTresLados(treino, validacao, teste)


# --- temperatura ------------------------------------------------------------


def aplicar_temperatura(logits: Sequence[Sequence[float]], temperatura: float) -> list[list[float]]:
    """Softmax de logits/T. T=1 e o softmax de sempre; T>1 achata, sem mudar o argmax."""
    if not temperatura > 0 or not math.isfinite(temperatura):
        raise ValueError(f"temperatura precisa ser positiva e finita, veio {temperatura}")
    z = np.asarray(logits, dtype=float) / temperatura
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return (e / e.sum(axis=1, keepdims=True)).tolist()


def _nll(logits: np.ndarray, rotulos: np.ndarray, temperatura: float) -> float:
    z = logits / temperatura
    z = z - z.max(axis=1, keepdims=True)
    log_p = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
    return float(-log_p[np.arange(len(rotulos)), rotulos].mean())


def ajustar_temperatura(
    logits: Sequence[Sequence[float]], rotulos: Sequence[int], *, iteracoes: int = 60
) -> float:
    """T que minimiza o NLL na VALIDACAO (Guo et al., 2017), entre 0,05 e 20.

    Busca de razao aurea em log T: um parametro, convexo na pratica.
    """
    z = np.asarray(logits, dtype=float)
    y = np.asarray(rotulos, dtype=int)
    if len(z) != len(y) or len(y) == 0:
        raise ValueError("logits e rotulos vazios ou de tamanhos diferentes")
    a, b = math.log(0.05), math.log(20.0)
    razao = (math.sqrt(5) - 1) / 2
    c, d = b - razao * (b - a), a + razao * (b - a)
    fc, fd = _nll(z, y, math.exp(c)), _nll(z, y, math.exp(d))
    for _ in range(iteracoes):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - razao * (b - a)
            fc = _nll(z, y, math.exp(c))
        else:
            a, c, fc = c, d, fd
            d = a + razao * (b - a)
            fd = _nll(z, y, math.exp(d))
    return float(math.exp((a + b) / 2))


# --- metricas e sementes ------------------------------------------------------


def metricas_completas(
    probabilidades: Sequence[Sequence[float]],
    rotulos: Sequence[int],
    *,
    nomes_classes: Sequence[str],
) -> dict:
    """Acuracia, F1-macro, F1 por classe, matriz e ECE de confianca."""
    probs = [list(map(float, p)) for p in probabilidades]
    rotulos = [int(r) for r in rotulos]
    if len(probs) != len(rotulos) or not rotulos:
        raise ValueError("probabilidades e rotulos vazios ou de tamanhos diferentes")
    classes = list(range(len(nomes_classes)))
    preditos = [int(np.argmax(p)) for p in probs]
    matriz = matriz_de_confusao(rotulos, preditos, classes=classes)
    return {
        "exemplos": len(rotulos),
        "acuracia": sum(p == r for p, r in zip(preditos, rotulos)) / len(rotulos),
        "f1_macro": f1_macro(rotulos, preditos, classes=classes),
        "por_classe": contagens_por_classe(matriz, list(nomes_classes)),
        "matriz": matriz,
        "ece": ece_multiclasse(probs, rotulos),
    }


def resumir_sementes(rodadas: Sequence[dict], *, chave: str = "f1_macro") -> dict:
    """Media, desvio amostral e a semente MEDIANA (a promovida)."""
    if len(rodadas) < 2:
        raise ValueError("uma semente so nao mede variancia: rode pelo menos duas")
    valores = np.asarray([float(r[chave]) for r in rodadas])
    ordem = sorted(rodadas, key=lambda r: float(r[chave]))
    mediana = ordem[(len(ordem) - 1) // 2]
    return {
        "chave": chave,
        "sementes": [r["semente"] for r in rodadas],
        "valores": valores.tolist(),
        "media": float(valores.mean()),
        "desvio": float(valores.std(ddof=1)),
        "semente_mediana": mediana["semente"],
    }


# --- argumentos -----------------------------------------------------------------


def argumentos_padrao(
    saida: str,
    *,
    semente: int,
    metrica: str = "f1_macro",
    epocas: int = 5,
    taxa: float = 2e-5,
    lote: int = 32,
    fp16: bool = True,
) -> dict:
    """Kwargs do `TrainingArguments` mais `paciencia` (do `EarlyStoppingCallback`).

    O notebook faz `paciencia = args.pop("paciencia")` e passa o resto. A
    avaliacao a cada epoca e na VALIDACAO -- quem passa `eval_dataset` e o
    notebook, e o teste nunca entra no `Trainer`.
    """
    return {
        "output_dir": saida,
        "seed": semente,
        "learning_rate": taxa,
        "num_train_epochs": epocas,
        "per_device_train_batch_size": lote,
        "per_device_eval_batch_size": lote * 2,
        "warmup_ratio": 0.1,
        "weight_decay": 0.01,
        "eval_strategy": "epoch",
        "save_strategy": "epoch",
        "save_total_limit": 2,
        "load_best_model_at_end": True,
        "metric_for_best_model": metrica,
        "greater_is_better": True,
        "fp16": fp16,
        "report_to": "none",
        "paciencia": 2,
    }


# --- o caminho unico de notebook e benchmark ------------------------------------

SEMENTE_DIVISAO = 42


def _recorte(exemplos, indices):
    from fraus.corpora import Exemplos

    return Exemplos(
        textos=[exemplos.textos[i] for i in indices],
        rotulos=[exemplos.rotulos[i] for i in indices],
        grupos=None if exemplos.grupos is None else [exemplos.grupos[i] for i in indices],
        nomes_classes=list(exemplos.nomes_classes),
    )


def preparar_divisao(
    exemplos,
    *,
    agrupar: bool = True,
    fracao_val: float = 0.10,
    fracao_teste: float = 0.15,
    semente: int = SEMENTE_DIVISAO,
) -> dict:
    """Duplicata fora, depois treino/validacao/teste -- o MESMO teste dos dois lados.

    O notebook treina em `treino`, escolhe epoca e temperatura em `validacao`;
    o benchmark mede em `teste`. `agrupar=False` ignora os grupos (corpus em
    que um grupo sozinho e grande demais para caber num lado).
    """
    limpos = _recorte(exemplos, remover_duplicatas(exemplos.textos, exemplos.rotulos).indices)
    grupos = limpos.grupos if agrupar else None
    divisao = dividir_treino_val_teste(
        limpos.rotulos, grupos=grupos, fracao_val=fracao_val, fracao_teste=fracao_teste,
        semente=semente,
    )
    return {
        "treino": _recorte(limpos, divisao.treino),
        "validacao": _recorte(limpos, divisao.validacao),
        "teste": _recorte(limpos, divisao.teste),
    }


def amostra_estratificada(exemplos, n: int, *, semente: int = SEMENTE_DIVISAO):
    """`n` exemplos na proporcao das classes; o conjunto inteiro se ja for menor."""
    if n >= len(exemplos.rotulos):
        return exemplos
    from sklearn.model_selection import train_test_split

    _, escolhidos = train_test_split(
        list(range(len(exemplos.rotulos))), test_size=n, random_state=semente,
        stratify=exemplos.rotulos,
    )
    return _recorte(exemplos, sorted(int(i) for i in escolhidos))


def pesos_de_classe(rotulos: Sequence[int], n_classes: int) -> list[float]:
    """n / (k * n_c): classe rara pesa mais na perda. Classe ausente pesa como se tivesse 1."""
    contagem = np.bincount(np.asarray(rotulos, dtype=int), minlength=n_classes)
    return (len(rotulos) / (n_classes * np.maximum(contagem, 1))).tolist()


ARQUIVO_RECEITA = "fraus_receita.json"


def treinar_uma_semente(
    *,
    modelo_base: str,
    lados: dict,
    semente: int,
    dir_checkpoint: str,
    dir_saida: str,
    tamanho_maximo: int = 192,
    ponderar_classes: bool = True,
    **ajustes,
) -> dict:
    """Treina uma semente, escolhe epoca e temperatura na validacao, mede o teste UMA vez.

    `lados` e o que `preparar_divisao` devolve. Grava modelo, tokenizador e
    `fraus_receita.json` (semente, temperatura, metricas) em `dir_saida`.
    `ajustes` sobrescreve `argumentos_padrao` (epocas, taxa, lote, fp16).
    torch/transformers so sao importados aqui dentro.
    """
    import json
    import os

    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        EarlyStoppingCallback,
        Trainer,
        TrainingArguments,
        set_seed,
    )

    set_seed(semente)
    nomes = list(lados["treino"].nomes_classes)
    tokenizador = AutoTokenizer.from_pretrained(modelo_base)

    class _Conjunto(torch.utils.data.Dataset):
        def __init__(self, exemplos):
            self.cod = tokenizador(list(exemplos.textos), truncation=True, max_length=tamanho_maximo)
            self.rotulos = list(exemplos.rotulos)

        def __len__(self):
            return len(self.rotulos)

        def __getitem__(self, i):
            item = {k: v[i] for k, v in self.cod.items()}
            item["labels"] = int(self.rotulos[i])
            return item

    treino, validacao, teste = (_Conjunto(lados[k]) for k in ("treino", "validacao", "teste"))
    modelo = AutoModelForSequenceClassification.from_pretrained(
        modelo_base, num_labels=len(nomes),
        id2label=dict(enumerate(nomes)), label2id={n: i for i, n in enumerate(nomes)},
    )
    pesos = torch.tensor(
        pesos_de_classe(lados["treino"].rotulos, len(nomes)) if ponderar_classes
        else [1.0] * len(nomes),
        dtype=torch.float32,
    )

    class _Ponderado(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            rotulos = inputs.pop("labels")
            saidas = model(**inputs)
            perda = torch.nn.functional.cross_entropy(
                saidas.logits, rotulos, weight=pesos.to(saidas.logits.device)
            )
            return (perda, saidas) if return_outputs else perda

    def _metricas(predicao):
        preditos = np.argmax(predicao.predictions, axis=1)
        return {"f1_macro": f1_macro(predicao.label_ids, preditos, classes=range(len(nomes)))}

    argumentos = argumentos_padrao(os.path.join(dir_checkpoint, f"semente-{semente}"),
                                   semente=semente, **ajustes)
    paciencia = argumentos.pop("paciencia")
    treinador = _Ponderado(
        model=modelo, args=TrainingArguments(**argumentos),
        train_dataset=treino, eval_dataset=validacao,  # NUNCA o teste
        data_collator=DataCollatorWithPadding(tokenizador), compute_metrics=_metricas,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=paciencia)],
    )
    treinador.train()

    logits_val = treinador.predict(validacao).predictions
    temperatura = ajustar_temperatura(logits_val, lados["validacao"].rotulos)
    f1_val = f1_macro(lados["validacao"].rotulos, np.argmax(logits_val, axis=1),
                      classes=range(len(nomes)))
    logits_teste = treinador.predict(teste).predictions  # a unica leitura do teste
    metricas_teste = metricas_completas(
        aplicar_temperatura(logits_teste, temperatura), lados["teste"].rotulos,
        nomes_classes=nomes,
    )
    metricas_teste["ece_sem_temperatura"] = metricas_completas(
        aplicar_temperatura(logits_teste, 1.0), lados["teste"].rotulos, nomes_classes=nomes
    )["ece"]

    from fraus.divisao import impressao_dos_textos

    resultado = {
        "semente": semente,
        "modelo_base": modelo_base,
        "temperatura": temperatura,
        "f1_macro_validacao": f1_val,
        "f1_macro": metricas_teste["f1_macro"],
        "epocas_treinadas": float(treinador.state.epoch or 0),
        "melhor_checkpoint": treinador.state.best_model_checkpoint,
        "tamanhos": {k: len(lados[k].rotulos) for k in ("treino", "validacao", "teste")},
        "impressao_teste": impressao_dos_textos(lados["teste"].textos),
        "teste": metricas_teste,
    }
    os.makedirs(dir_saida, exist_ok=True)
    treinador.save_model(dir_saida)
    tokenizador.save_pretrained(dir_saida)
    with open(os.path.join(dir_saida, ARQUIVO_RECEITA), "w", encoding="utf-8") as arquivo:
        json.dump(resultado, arquivo, ensure_ascii=False, indent=2)
    return resultado


def prever_probabilidades(
    dir_modelo: str, textos: Sequence[str], *, temperatura: float = 1.0, lote: int = 64,
    tamanho_maximo: int = 192,
) -> list[list[float]]:
    """Probabilidades com a temperatura do artefato; GPU se houver. Para conjunto independente."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizador = AutoTokenizer.from_pretrained(dir_modelo)
    modelo = AutoModelForSequenceClassification.from_pretrained(dir_modelo).to(dispositivo).eval()
    logits: list[list[float]] = []
    with torch.inference_mode():
        for inicio in range(0, len(textos), lote):
            entradas = tokenizador(
                list(textos[inicio:inicio + lote]), truncation=True, max_length=tamanho_maximo,
                padding=True, return_tensors="pt",
            ).to(dispositivo)
            logits.extend(modelo(**entradas).logits.float().cpu().tolist())
    return aplicar_temperatura(logits, temperatura) if logits else []


def juntar(*partes):
    """Concatena Exemplos com as MESMAS classes na mesma ordem (invariante 8)."""
    from fraus.corpora import Exemplos

    nomes = list(partes[0].nomes_classes)
    if any(list(p.nomes_classes) != nomes for p in partes):
        raise ValueError("so junta corpora com as mesmas classes, na mesma ordem")
    saida = Exemplos(grupos=[], nomes_classes=nomes)
    for p in partes:
        saida.textos += list(p.textos)
        saida.rotulos += list(p.rotulos)
        saida.grupos += list(p.grupos) if p.grupos is not None else [""] * len(p.textos)
    return saida
