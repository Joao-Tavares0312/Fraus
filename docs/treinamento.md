# Treinamento do classificador de satisfacao (BERTimbau)

Este documento explica como rodar o notebook `notebooks/01_treino_bertimbau.ipynb`, que faz o fine-tune de um classificador de texto em 3 classes (insatisfeito, neutro, satisfeito) a partir do modelo `neuralmind/bert-base-portuguese-cased`, usando o corpus B2W-Reviews01.

O treino roda inteiramente no Google Colab, fora deste repositorio — nao ha teste automatizado local para essa etapa porque ela exige GPU.

## Como abrir no Colab

1. Va em [colab.research.google.com](https://colab.research.google.com).
2. `Arquivo > Fazer upload de notebook` e selecione `notebooks/01_treino_bertimbau.ipynb` (ou abra direto do GitHub se o repositorio estiver acessivel a partir da sua conta).

## Exigencia de GPU

O notebook so funciona com acelerador de GPU habilitado. Antes de rodar qualquer celula:

`Ambiente de execucao > Alterar tipo de ambiente de execucao > GPU`

A primeira celula do notebook faz `assert torch.cuda.is_available()` e falha com uma mensagem explicita se o ambiente de execucao estiver sem GPU.

## Onde o checkpoint fica no Drive

O notebook monta o Google Drive (`drive.mount('/content/drive')`) e usa dois diretorios dentro dele, para sobreviver a uma queda de sessao do Colab — o mesmo padrao ja usado no notebook de RVC do projeto Neuro-ai:

- `/content/drive/MyDrive/dolos/checkpoints` — checkpoints intermediarios salvos pelo `Trainer` a cada epoca (`save_strategy="epoch"`, `save_total_limit=2`). Se a sessao cair, o proximo `Trainer.train()` pode retomar a partir do ultimo checkpoint salvo aqui.
- `/content/drive/MyDrive/dolos/modelos/bertimbau-satisfacao` — destino final do modelo treinado, do tokenizador e do `metricas.json`, escritos na ultima celula do notebook.

## Para onde copiar o artefato no repo local

Depois que o notebook terminar (celula de avaliacao e export), baixe a pasta `dolos/modelos/bertimbau-satisfacao` do Google Drive e copie o conteudo para:

```
modelos/bertimbau-satisfacao/
```

na raiz deste repositorio. Os arquivos esperados sao:

- `config.json`
- `model.safetensors`
- `tokenizer.json`
- `tokenizer_config.json`
- `special_tokens_map.json`
- `metricas.json` — `{"acuracia": float, "f1_macro": float, "classes": ["insatisfeito", "neutro", "satisfeito"]}`

A Task 7 carrega esse diretorio para servir o classificador.

**Importante:** `modelos/` esta no `.gitignore` deste repositorio. O artefato do modelo treinado (pesos, tokenizer, metricas) **nao vai para o git** — ele fica local, versionado apenas via o checkpoint no Drive.

## Mapeamento de rotulo

O rotulo de satisfacao vem do campo `overall_rating` (nota de 1 a 5) do B2W-Reviews01:

| `overall_rating` | rotulo       | indice |
|-------------------|--------------|--------|
| 1–2                | insatisfeito | 0      |
| 3                  | neutro       | 1      |
| 4–5                | satisfeito   | 2      |

O corpus e balanceado por subamostragem da classe majoritaria antes do split de treino/teste, porque as notas 4-5 dominam o corpus e enviesariam o classificador.

## Nota sobre o NPS inferido (nao implementado nesta etapa)

O campo `recommend_to_a_friend` do B2W-Reviews01 fica reservado como ancora para um NPS inferido, a ser implementado numa etapa posterior (Task 9). Este notebook nao usa esse campo — ele treina apenas o classificador de satisfacao de 3 classes.
