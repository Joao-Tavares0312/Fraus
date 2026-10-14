# E4 — Benchmark: Fraus × LLM genérico

> Estado: **descartado pelo João em 14/10/2026**, antes de qualquer código.
> Fica registrado como alternativa recusada. Sem o benchmark, nenhum documento
> ou slide compara o Fraus com LLM em número: a tese "sem LLM" se sustenta
> pelo que é medido no próprio Fraus (explicação exata, calibração,
> determinismo por construção), não por comparação. Faz parte de
> [Diferenciais](2026-10-14-diferenciais-visao-geral.md).

## Objetivo

Medir, nas mesmas conversas e na mesma ordem, onde o Fraus ganha e onde o LLM
genérico ganha: acerto, latência, custo, determinismo e robustez.

**A comparação é com LLM genérico, não com produto comercial.**

## Desenho

**1. Isolamento (regra 8).**

- **Onde mora o código:** `scripts/benchmark/`. A dependência do SDK entra
  num extra opcional `benchmark` do `pyproject`, e **nunca** em
  `requirements.txt`, que é o que a Vercel instala.
- **Guarda de import:** um teste falha se algum arquivo de `fraus/` importar
  SDK de LLM.
- **Chave:** só por variável de ambiente.
- **Fora do pacote da API:** `.vercelignore` passa a excluir
  `scripts/benchmark/` e `benchmark/`.

**2. Conjunto.**

- **Principal:** o holdout B2W de 300 conversas, montado com texto público de
  resenha e estrutura do simulador. Nenhum dado de cliente, e por isso pode
  ir em prompt.
- **A mesma lista de IDs, na mesma ordem**, para os dois lados.
- **Robustez:** variantes geradas por regra com semente fixa (gíria, typo,
  CAIXA ALTA, emoji), aplicadas só às falas do cliente.

**3. Cliente LLM.**

- Uma interface pequena com `responder(prompt) -> (texto, tokens_in,
  tokens_out, latencia)`. Há duas implementações: a real (SDK) e a **falsa**,
  sem rede, usada nos testes.
- **Prompts:** zero-shot e few-shot (k = 6, exemplos tirados do **treino**,
  nunca do teste).
- **Saída pedida:** JSON `{"classe": 0|1|2}`. JSON inválido ou classe fora do
  domínio conta como **erro**, não é descartado.
- **Cache:** toda resposta bruta vai para `benchmark/saidas/*.jsonl`, com
  chave hash(modelo, prompt). Rodar de novo não paga duas vezes.
- **`--dry-run`:** conta os tokens do prompt (estimativa local, declarada
  como tal) e multiplica por `precos.toml`, sem chave.

**4. Métricas** (`benchmark/resultados/AAAA-MM-DD.json`, gráficos em PNG por
script e `docs/diferenciais/benchmark.md`):

- **Acerto:** acurácia e F1-macro, com IC por bootstrap (1.000 reamostras,
  semente fixa).
- **Latência:** p50, p95 e p99. Para o Fraus, frio (primeira predição depois
  de carregar) e aquecido, com a máquina declarada.
- **Custo por 1.000 conversas:**
  - Fraus: premissa de infraestrutura explícita (CPU, tempo medido, preço da
    hora de uma instância de referência citada com fonte).
  - LLM: tokens reais × `precos.toml`, com fonte e data em cada linha.
- **Determinismo:** N = 5 repetições em 50 conversas. Concordância entre
  repetições e variância da nota. O Fraus deve dar variância 0, e isso é
  medido, não suposto.
- **Robustez:** queda de acurácia por variante.
- **Privacidade:** tabela **qualitativa**, rotulada "análise", sem número
  inventado.

**5. Declarações obrigatórias no relatório.**

- O fusor foi treinado **nesta distribuição**.
- O tempo sintético favorece o Fraus.
- O prompt do LLM é ajustável e não foi otimizado à exaustão.
- **Onde o LLM ganha,** por exemplo em ironia e em texto longo, é reportado
  como saiu.

## Métrica de aceitação

Testes **sem rede**, com o cliente falso, cobrindo:

- parsing: JSON válido, inválido e classe fora do domínio;
- cache: o segundo run não chama o cliente;
- bootstrap: semente fixa dá IC reprodutível;
- custo: conta com `precos.toml` de teste;
- `--dry-run` funcionando sem chave;
- a guarda de import de `fraus/`.

## Dados

Holdout B2W mais variantes. Os resultados reais dependem da chave, dos preços
e dos pesos do Fraus.

## Limitações declaradas

- O conjunto é o do treino do Fraus (vantagem dele).
- O texto é de resenha, não de atendimento.
- O preço é do dia registrado.
- Um único conjunto de prompts.

## Fora de escopo

- Comparar com produto comercial.
- Fine-tuning de LLM.
- Usar LLM em `fraus/`.
