# Arquitetura

```
CSV / Discord / WhatsApp
        ↓  adapter de ingestão (fraus/ingest/)
   Conversa  ← modelo canônico único (fraus/modelos.py)
        ↓
 ┌────────┬────────┬────────┬────────┬────────┬────────┬────────┬────────────┐
 │texto   │emoji   │tempo   │emoção  │léxico  │ironia  │estilo  │incongruência│
 │BERTimbau│lexicon│latência│7 clas- │SentiLex│cabeça  │caixa   │emoji ×      │
 │por msg │+posição│escala- │ses +   │-PT02 + │binária │alta +  │texto        │
 │        │        │ção     │desprezo│negação │  (*)   │palavrão│             │
 └───┬────┴───┬────┴───┬────┴───┬────┴───┬────┴────────┴───┬────┴──────┬──────┘
            ↓  39 features                    (*) por mensagem, direto p/ a tela
      Fusor (LogisticRegression + StandardScaler)
            ↓  score 0–100
   nota 0–10 → categoria NPS → indicadores agregados
            ↓
      FastAPI  →  dashboard Next.js
```

## A decisão que explica o desenho

**Um modelo canônico, muitos adaptadores.** CSV, Totalk, transcrição de
`.docx`/`.pdf` e webhook desembocam todos em `Conversa` — e o resto do sistema
não sabe de onde o dado veio. Adicionar uma fonte é escrever um adaptador, não
tocar em sinal, fusor ou indicador.

## As sete famílias que pontuam

| família | o que mede | por que existe |
|---|---|---|
| **texto** | P(insatisfeito/neutro/satisfeito) por mensagem | o sinal principal — o único fine-tunado para a tarefa |
| **emoji** | polaridade e **posição relativa** | emoji no fim da conversa não vale o mesmo que no começo |
| **tempo** | latências, escalação, abandono | espera longa degrada satisfação (literatura de live chat) |
| **emoção** | 7 de Ekman + desprezo derivado | raiva e frustração distinguem *tipos* de insatisfação |
| **léxico** | SentiLex-PT02 com escopo de negação | âncora determinística, auditável, imune a retreino |
| **estilo** | caixa alta, alongamento, palavrão, censura | intensidade que o classificador de sentença perde |
| **incongruência** | elogio convivendo com situação negativa | é o que alcança a frase canônica do projeto |

## A ironia continua carregada, e não pontua

A oitava cabeça existe, é obrigatória para a API subir e aparece na tela **por
mensagem** — mas **saiu do vetor** em 04/09/2026.

Medida no próprio corpus de treino do fusor (B2W-Reviews01), ela marca **74% das
resenhas satisfeitas** como irônicas contra **9% das insatisfeitas**: naquele
corpus ela é um detector de sentimento **positivo**, não de ironia. O fusor
aprendeu peso **+0,77** para `ironia_prob_media`, empurrando ironia para
*satisfeito* — o inverso do que o nome promete.

> **Feature que mede outra coisa que não o nome dela é pior que feature
> ausente.** Ela some do vetor sem que ninguém perceba a inversão, porque a
> acurácia global continua ótima.

Ver [Treinamento](treinamento.md) para a medição completa.

## Onde cada coisa mora

| caminho | responsabilidade |
|---|---|
| `fraus/modelos.py` | `Conversa` / `Mensagem` — o modelo canônico |
| `fraus/ingest/` | adaptadores de entrada, um por formato |
| `fraus/sinais/` | as oito famílias de sinal |
| `fraus/fusor.py` | `NOMES_FEATURES` (39) e o `Fusor` |
| `fraus/indicadores.py` | NPS, CSAT, contenção, falso containment, série |
| `fraus/evidencia.py` | evidência fraca — a cabeça tracejada |
| `fraus/deriva.py` | deriva de distribuição — a invariante 10 em runtime |
| `fraus/api/` | FastAPI: `criar_app` (fábrica) e as rotas por domínio |
| `dashboard/` | Next.js — ver [Design](design.md) |
