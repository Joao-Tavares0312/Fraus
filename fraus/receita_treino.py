"""A receita de treino comum aos notebooks 01 (satisfacao), 03 (emocao) e 04 (ironia).

Ate 19/10/2026 os tres notebooks passavam `eval_dataset=divisao['test']` com
`load_best_model_at_end=True`: a melhor epoca era escolhida NO TESTE, e o
numero reportado era um segundo `evaluate()` nesse mesmo teste. Nao havia
validacao. Os 0,782 da satisfacao e os 0,584 da emocao sao, por isso,
otimistas por construcao.

A regra daqui em diante:

- duplicata por texto normalizado sai ANTES de dividir (o GoEmotions-PT tem a
  mesma frase curta com ids diferentes, que caiam dos dois lados);
- tres lados: treino e validacao escolhem epoca, semente e temperatura; o
  teste so e aberto por `avaliar_teste_final`, depois da selecao congelada;
- tres sementes, media e desvio reportados, com a semente mediana pela
  VALIDACAO -- nunca pela metrica do teste;
- a temperatura e ajustada na validacao e gravada no artefato;
- curvas comparam treino diagnostico fixo em eval e validacao, nao a perda
  dos minibatches com dropout.

As funcoes puras nao importam torch. Treino e inferencia carregam dependencias
pesadas apenas quando chamados; nao alteram o motor de runtime.
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


def resumir_sementes(rodadas: Sequence[dict], *, chave: str = "f1_macro_validacao") -> dict:
    """Media, desvio amostral e semente mediana; selecao padrao na validacao."""
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
ARQUIVO_AVALIACAO_FINAL = "avaliacao_final.json"


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
    """Treina e seleciona somente na validacao; o teste fornece apenas manifesto.

    `lados` vem de `preparar_divisao`. Grava modelo, tokenizador e receita com
    curvas, argumentos efetivos e manifestos, sem tokenizar ou inferir teste.
    `ajustes` sobrescreve `argumentos_padrao` (epocas, taxa, lote, fp16).
    A avaliacao final e uma operacao separada, depois de congelar a selecao.
    """
    import copy
    import json
    import os
    import random

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

    treino, validacao = (_Conjunto(lados[k]) for k in ("treino", "validacao"))
    exemplos_diagnostico = amostra_estratificada(lados["treino"], 2000, semente=42)
    diagnostico = _Conjunto(exemplos_diagnostico)
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

        def evaluate(self, *args, **kwargs):
            # So a avaliacao normal pode acionar callbacks/early stopping.
            metricas = super().evaluate(*args, **kwargs)
            modelo_avaliado = self.model_wrapped
            modos = [(modulo, modulo.training) for modulo in modelo_avaliado.modules()]
            estado_python, estado_numpy = random.getstate(), np.random.get_state()
            perdas, reais, preditos = [], [], []
            try:
                # Criar/iterar DataLoader consome RNG mesmo sem embaralhamento.
                # Diagnostico nao pode mudar a trajetoria dos passos seguintes.
                with torch.random.fork_rng(
                    devices=list(range(torch.cuda.device_count()))
                ), torch.inference_mode():
                    modelo_avaliado.eval()
                    for entradas in self.get_eval_dataloader(diagnostico):
                        perda, logits, rotulos = self.prediction_step(
                            modelo_avaliado, entradas, prediction_loss_only=False
                        )
                        perda, logits, rotulos = self.accelerator.gather_for_metrics((
                            perda.repeat(rotulos.shape[0]), logits, rotulos,
                        ))
                        # Mesmo peso por exemplo/batch usado no eval_loss do Trainer.
                        perdas.extend(perda.float().cpu().tolist())
                        reais.extend(rotulos.cpu().tolist())
                        preditos.extend(logits.argmax(dim=-1).cpu().tolist())
            finally:
                random.setstate(estado_python)
                np.random.set_state(estado_numpy)
                for modulo, modo in modos:
                    modulo.training = modo
            # Registrar nao dispara callbacks nem modifica TrainerControl.
            self.state.log_history.append({
                "diagnostico_treino_loss": float(np.mean(perdas)),
                "diagnostico_treino_f1_macro": f1_macro(
                    reais, preditos, classes=range(len(nomes))
                ),
                "diagnostico_validacao_loss": float(metricas["eval_loss"]),
                "diagnostico_validacao_f1_macro": float(metricas["eval_f1_macro"]),
                "epoch": self.state.epoch,
                "step": self.state.global_step,
            })
            return metricas

    def _metricas(predicao):
        preditos = np.argmax(predicao.predictions, axis=1)
        return {"f1_macro": f1_macro(predicao.label_ids, preditos, classes=range(len(nomes)))}

    argumentos = argumentos_padrao(os.path.join(dir_checkpoint, f"semente-{semente}"),
                                   semente=semente, **ajustes)
    paciencia = argumentos.pop("paciencia")
    # O transformers 5 tirou o `warmup_ratio` (o Colab ja vem com ele; a 4.x
    # local aceitava). Passos inteiros valem nas duas versoes.
    passos_por_epoca = math.ceil(len(treino) / argumentos["per_device_train_batch_size"])
    argumentos["warmup_steps"] = int(
        argumentos.pop("warmup_ratio") * passos_por_epoca * argumentos["num_train_epochs"]
    )
    treinador = _Ponderado(
        model=modelo, args=TrainingArguments(**argumentos),
        train_dataset=treino, eval_dataset=validacao,  # NUNCA o teste
        data_collator=DataCollatorWithPadding(tokenizador), compute_metrics=_metricas,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=paciencia)],
    )
    treinador.train()

    logits_val = treinador.predict(validacao, metric_key_prefix="validacao_final").predictions
    temperatura = ajustar_temperatura(logits_val, lados["validacao"].rotulos)
    f1_val = f1_macro(lados["validacao"].rotulos, np.argmax(logits_val, axis=1),
                      classes=range(len(nomes)))
    # Copia antes que os notebooks removam os checkpoints. Inclui o log original
    # do Trainer e um registro comparavel treino/validacao por epoca.
    historico = copy.deepcopy(treinador.state.log_history)
    avaliacoes = [r for r in historico if "eval_f1_macro" in r]
    melhor_epoca = max(avaliacoes, key=lambda r: r["eval_f1_macro"])["epoch"]

    from fraus.divisao import impressao_dos_textos
    from fraus.generalizacao import fingerprint_exemplos

    resultado = {
        "semente": semente,
        "modelo_base": modelo_base,
        "temperatura": temperatura,
        "f1_macro_validacao": f1_val,
        "tamanho_maximo": tamanho_maximo,
        "ponderar_classes": ponderar_classes,
        "pesos_de_classe": pesos.tolist(),
        "epocas_treinadas": float(treinador.state.epoch or 0),
        "melhor_checkpoint": treinador.state.best_model_checkpoint,
        "tamanhos": {k: len(lados[k].rotulos) for k in ("treino", "validacao", "teste")},
        "impressao_teste": impressao_dos_textos(lados["teste"].textos),
        "historico": historico,
        "argumentos_efetivos": {
            **treinador.args.to_dict(), "paciencia": paciencia,
        },
        "melhor_epoca": float(melhor_epoca),
        "diagnostico_treino": {
            "semente": 42,
            "exemplos": len(exemplos_diagnostico.textos),
            "fingerprint": fingerprint_exemplos(exemplos_diagnostico),
        },
        "manifesto_divisao": {
            lado: {
                "fingerprint": fingerprint_exemplos(exemplos),
                "impressao_textos": impressao_dos_textos(exemplos.textos),
                "exemplos": len(exemplos.textos),
            }
            for lado, exemplos in lados.items()
        },
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
    return aplicar_temperatura(
        _prever_logits(dir_modelo, textos, lote=lote, tamanho_maximo=tamanho_maximo), temperatura
    ) if len(textos) else []


def _prever_logits(
    dir_modelo: str, textos: Sequence[str], *, lote: int = 64, tamanho_maximo: int = 192,
) -> list[list[float]]:
    """Uma inferencia compartilhada: permite calibrar sem inverter um softmax."""
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
    return logits


def avaliar_teste_final(*, dir_modelo: str, exemplos, manifesto_esperado: str) -> dict:
    """Abre o teste congelado, sem selecionar ou modificar a receita do candidato.

    O chamador congela configuracao e selecao na validacao antes desta chamada.
    Fingerprint recebido, conjunto e manifesto salvo precisam ser identicos,
    inclusive rotulos, grupos efetivos e ordem das classes, antes da inferencia.
    """
    import hashlib
    import json
    from pathlib import Path

    from fraus.divisao import impressao_dos_textos
    from fraus.generalizacao import fingerprint_exemplos

    pasta = Path(dir_modelo)
    receita = json.loads((pasta / ARQUIVO_RECEITA).read_text(encoding="utf-8"))
    fingerprint = fingerprint_exemplos(exemplos)
    salvo = receita.get("manifesto_divisao", {}).get("teste", {}).get("fingerprint")
    if not manifesto_esperado or fingerprint != manifesto_esperado or salvo != fingerprint:
        raise ValueError("manifesto de teste divergente")

    # Os mesmos logits alimentam ambas as metricas: desfazer softmax pode perder
    # informacao quando uma probabilidade underflowa para zero.
    logits = _prever_logits(
        dir_modelo, exemplos.textos, tamanho_maximo=receita["tamanho_maximo"]
    )
    temperatura = receita["temperatura"]
    resultado = metricas_completas(
        aplicar_temperatura(logits, temperatura), exemplos.rotulos,
        nomes_classes=exemplos.nomes_classes,
    )
    resultado["ece_sem_temperatura"] = metricas_completas(
        aplicar_temperatura(logits, 1.0), exemplos.rotulos,
        nomes_classes=exemplos.nomes_classes,
    )["ece"]
    # Hash apenas de pesos/configuracao/tokenizador. Manifestos de retomada ou
    # exportacao podem ser criados depois, sem mudar a identidade do modelo.
    arquivos_de_inferencia = {
        "config.json", "tokenizer.json", "tokenizer_config.json",
        "special_tokens_map.json", "added_tokens.json", "vocab.txt", "vocab.json",
        "merges.txt", "spiece.model", "sentencepiece.bpe.model", "chat_template.jinja",
        "model.safetensors.index.json", "pytorch_model.bin.index.json",
    }
    hashes = {}
    for caminho in sorted(pasta.iterdir()):
        peso = (
            caminho.name.startswith("model") and caminho.suffix == ".safetensors"
        ) or (
            caminho.name.startswith("pytorch_model") and caminho.suffix == ".bin"
        )
        if not caminho.is_file() or not (peso or caminho.name in arquivos_de_inferencia):
            continue
        with caminho.open("rb") as arquivo:
            hashes[caminho.name] = hashlib.file_digest(arquivo, "sha256").hexdigest()
    resultado.update({
        "semente": receita["semente"],
        "temperatura": temperatura,
        "tamanho_maximo": receita["tamanho_maximo"],
        "fingerprint_teste": fingerprint,
        "impressao_teste": impressao_dos_textos(exemplos.textos),
        "hashes_modelo": hashes,
        "hash_modelo": hashlib.sha256(json.dumps(
            hashes, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest(),
    })
    (pasta / ARQUIVO_AVALIACAO_FINAL).write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    return resultado


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
