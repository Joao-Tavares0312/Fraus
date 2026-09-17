"""Destila as tres cabecas atuais em um unico encoder e exporta para ONNX.

O corpus e apenas texto (CSV com coluna ``texto``, JSONL com ``texto`` ou um
TXT com uma frase por linha). Os tres checkpoints atuais atuam como professores;
assim o alvo e preservar o comportamento ja validado, nao inventar rotulos.

Uso em uma maquina com GPU/Colab::

    uv sync --extra treino
    uv run python scripts/treinar_multitarefa.py corpus.csv --epocas 3

O resultado fica em ``modelos-onnx/bertimbau-multitarefa-candidato``. Ele nao e
promovido automaticamente: rode ``scripts/comparar_backends.py --multitarefa``.
"""

import argparse
import csv
import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

NOMES = ("satisfacao", "emocao", "ironia")
CLASSES = (3, 7, 2)


def ler_textos(caminho: Path) -> list[str]:
    """Le corpus sem transformar dado ausente em texto vazio."""
    sufixo = caminho.suffix.lower()
    if sufixo == ".jsonl":
        textos = [json.loads(linha)["texto"] for linha in caminho.read_text(encoding="utf-8").splitlines() if linha.strip()]
    elif sufixo == ".csv":
        with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
            textos = [linha["texto"] for linha in csv.DictReader(arquivo)]
    else:
        textos = caminho.read_text(encoding="utf-8").splitlines()
    return list(dict.fromkeys(t.strip() for t in textos if isinstance(t, str) and t.strip()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--epocas", type=int, default=3)
    parser.add_argument("--lote", type=int, default=16)
    parser.add_argument("--taxa", type=float, default=2e-5)
    parser.add_argument("--semente", type=int, default=42)
    parser.add_argument("--validacao", type=float, default=0.15)
    parser.add_argument(
        "--destino",
        type=Path,
        default=RAIZ / "modelos-onnx" / "bertimbau-multitarefa-candidato",
    )
    opcoes = parser.parse_args()
    if opcoes.destino.exists():
        raise SystemExit(f"destino ja existe; nao vou sobrescrever: {opcoes.destino}")

    import numpy as np
    import torch
    from torch import nn
    from torch.nn import functional as F
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

    random.seed(opcoes.semente)
    torch.manual_seed(opcoes.semente)
    textos = ler_textos(opcoes.corpus)
    if len(textos) < 100:
        raise SystemExit("corpus pequeno demais: use ao menos 100 textos diversos")
    random.shuffle(textos)
    corte = max(1, round(len(textos) * (1 - opcoes.validacao)))
    treino, validacao = textos[:corte], textos[corte:]
    dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    origem = RAIZ / "modelos"
    tokenizer = AutoTokenizer.from_pretrained(origem / "bertimbau-satisfacao")

    professores = []
    for nome in NOMES:
        modelo = AutoModelForSequenceClassification.from_pretrained(origem / f"bertimbau-{nome}")
        professores.append(modelo.eval().to(dispositivo))

    class Multitarefa(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = AutoModel.from_pretrained(origem / "bertimbau-satisfacao")
            oculto = self.encoder.config.hidden_size
            self.cabecas = nn.ModuleList(nn.Linear(oculto, n) for n in CLASSES)
            for cabeca, professor in zip(self.cabecas, professores):
                cabeca.load_state_dict(professor.classifier.state_dict())

        def forward(self, input_ids, attention_mask, token_type_ids=None):
            saida = self.encoder(input_ids=input_ids, attention_mask=attention_mask,
                                 token_type_ids=token_type_ids).last_hidden_state[:, 0]
            return tuple(cabeca(saida) for cabeca in self.cabecas)

    class Textos(Dataset):
        def __init__(self, itens): self.itens = itens
        def __len__(self): return len(self.itens)
        def __getitem__(self, indice): return self.itens[indice]

    def juntar(lote):
        return tokenizer(lote, truncation=True, max_length=192, padding=True, return_tensors="pt")

    aluno = Multitarefa().to(dispositivo)
    otimizador = torch.optim.AdamW(aluno.parameters(), lr=opcoes.taxa)
    carregador = DataLoader(Textos(treino), batch_size=opcoes.lote, shuffle=True, collate_fn=juntar)
    for epoca in range(opcoes.epocas):
        aluno.train()
        perda_total = 0.0
        for entradas in carregador:
            entradas = {k: v.to(dispositivo) for k, v in entradas.items()}
            with torch.no_grad():
                alvos = [p(**entradas).logits for p in professores]
            saidas = aluno(**entradas)
            perda = sum(F.kl_div(F.log_softmax(s, dim=-1), F.softmax(a, dim=-1), reduction="batchmean")
                        for s, a in zip(saidas, alvos))
            otimizador.zero_grad(set_to_none=True)
            perda.backward()
            otimizador.step()
            perda_total += float(perda)
        print(f"epoca {epoca + 1}/{opcoes.epocas}: perda={perda_total / len(carregador):.5f}")

    aluno.eval()
    divergencias = dict.fromkeys(NOMES, 0)
    total = 0
    with torch.inference_mode():
        for inicio in range(0, len(validacao), opcoes.lote):
            entradas = juntar(validacao[inicio:inicio + opcoes.lote])
            entradas = {k: v.to(dispositivo) for k, v in entradas.items()}
            saidas = aluno(**entradas)
            for nome, saida, professor in zip(NOMES, saidas, professores):
                referencia = professor(**entradas).logits
                divergencias[nome] += int((saida.argmax(-1) != referencia.argmax(-1)).sum())
            total += len(next(iter(entradas.values())))
    print("divergencias de classe na validacao:", {k: f"{v}/{total}" for k, v in divergencias.items()})

    opcoes.destino.mkdir(parents=True)
    tokenizer.save_pretrained(opcoes.destino)
    amostra = juntar(["amostra de exportacao"])
    amostra = tuple(amostra[k].to(dispositivo) for k in ("input_ids", "attention_mask", "token_type_ids"))
    torch.onnx.export(
        aluno, amostra, opcoes.destino / "model.onnx",
        input_names=["input_ids", "attention_mask", "token_type_ids"],
        output_names=["satisfacao_logits", "emocao_logits", "ironia_logits"],
        dynamic_axes={nome: {0: "lote", 1: "sequencia"} for nome in ("input_ids", "attention_mask", "token_type_ids")}
        | {nome: {0: "lote"} for nome in ("satisfacao_logits", "emocao_logits", "ironia_logits")},
        opset_version=17,
    )
    (opcoes.destino / "metricas_destilacao.json").write_text(
        json.dumps({"textos_treino": len(treino), "textos_validacao": total,
                    "divergencias": divergencias, "semente": opcoes.semente}, indent=2),
        encoding="utf-8",
    )
    print(f"candidato exportado em {opcoes.destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
