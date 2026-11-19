# Slides da banca de 09/12/2026 — rascunho

Texto dos 12 slides, para montar no editor de apresentação. Cada número tem
fonte e data ao lado; todo NPS leva a palavra **inferido**. A demo ao vivo
segue [o roteiro](../diferenciais/roteiro-demo.md).

## 1. Título

**Fraus** — satisfação em atendimentos por chatbot, sem perguntar ao cliente e
sem LLM em runtime. Nome, curso, orientador, 09/12/2026. Monograma FR.

## 2. O problema

- A pesquisa de NPS chega a poucos clientes e depois do atendimento.
- “ok, obrigado 🙂” encerra muita conversa e não diz se o cliente saiu
  satisfeito.
- Pergunta do trabalho: dá para **estimar** a satisfação a partir da própria
  conversa — texto, emoji e tempo — e dizer o quanto essa estimativa vale?

## 3. A tese e o requisito

- Estimar, não perguntar: a nota é **inferida** do texto e sempre rotulada
  como estimativa.
- Requisito do trabalho: **nenhum LLM no caminho de predição**. Classificadores
  locais em CPU e um fusor linear. Motivos: custo, latência, determinismo e
  explicação exata.
- Ausência de dado não é insatisfação: conversa sem fala do cliente fica
  “sem sinal”, nunca zero.

## 4. Arquitetura

Diagrama do README (“Arquitetura em uma tela”): CSV/Telegram/webhook →
`Conversa` canônica → famílias de sinal → 39 features → fusor (regressão
logística + StandardScaler) → score 0–100 → nota 0–10 → categoria NPS → API
FastAPI → dashboard Next.js. Dashboard e API são deploys separados.

## 5. Sete famílias, 39 features

Texto (BERTimbau por mensagem), emoji (lexicon + posição), tempo (latência,
escalação, abandono), emoção (7 classes + desprezo derivado), léxico
(SentiLex-PT02 com negação), estilo (caixa alta, pontuação, palavrão) e
incongruência (emoji × texto). A ironia é lida por mensagem e mostrada, mas
saiu do vetor em 04/09/2026: no corpus de treino ela media sentimento
positivo, não ironia (`docs/treinamento.md`).

## 6. Treino e a lição do 99,3%

- O primeiro fusor marcou **99,3% de acurácia** e era inútil: o simulador dava
  faixas de latência disjuntas por classe, e o modelo lia o relógio com o
  BERTimbau apagado (`docs/treinamento.md`).
- Regra que ficou (invariante 10): distribuições por rótulo se sobrepõem;
  acurácia alta demais é sintoma, não vitória.
- O mesmo sintoma reapareceu em 19/11 no holdout B2W com tempo sintético
  (acurácia 0,973) e foi registrado como tal, não como desempenho.

## 7. Resultados medidos (com fonte e data)

| cabeça | conjunto de teste | F1-macro | fonte |
|---|---|---|---|
| satisfação | B2W, 5.000 | 0,7646 | `docs/generalizacao.md`, 29/10 e 13/11/2026 |
| satisfação | ConsumerBR, 5.000 (fora do domínio de treino) | 0,5388 | idem |
| emoção | GoEmotions-PT, 7.328 | 0,6910 | `docs/generalizacao.md`, 26/10/2026 |
| ironia | MultiPICo-PT, 462 | 0,6603 | idem, cabeça em produção desde 13/11 |

Leitura honesta: a queda B2W → ConsumerBR é o tamanho do problema de
generalização. Conformal (E2): cobertura 0,940 no holdout B2W com alvo 0,9 —
**não** é cobertura em atendimento real (`docs/diferenciais/relatorio.md`).

## 8. Demonstração ao vivo

Lumen Telecom (fictícia): `tese` → `espera` com contrafactual de 60 s →
`0145` com abstenção → Radar → Replay. Ver o roteiro. Plano B local, sem rede,
ensaiado.

## 9. Integração com o Tars e o voto do cliente

- O Tars manda cada atendimento por `POST /ingestao`; o id leva um HMAC do
  chat, nunca o número do Telegram.
- O botão Resolveu / Não resolveu vai junto e aparece como **Voto do
  cliente**: concordância com a estimativa, sempre com o denominador.
- “Resolveu” é resolução, não nota NPS; com poucos votos é ilustração do
  ciclo, não validação. Capturas de produção em `~/fraus-backups/capturas-banca/`.

## 10. O que o Fraus não faz

Tabela da seção 5 do roteiro: não pontua atendente, não alerta ao vivo, não
decide sozinho, não usa LLM na predição, não afirma causa, não troca ausência
por zero, não chama de NPS declarado.

## 11. Limitações

- Sinal de tempo treinado em conversas sintéticas: nenhum corpus público em
  português traz timestamp de diálogo.
- Ironia fraca e fora do vetor.
- Generalização fora do domínio inconclusiva (ConsumerBR 0,5388).
- Dados da demo fabricados; atendimentos reais poucos.
- Atendimentos do Tars anteriores a 19/11 ainda têm o `chat_id` no id.

## 12. Trabalho futuro

E3 (nota declarada × inferida, exige schema aprovado), exports reais de
Discord/Zendesk/Blip, Web Vitals de campo, retreino com dado de suporte
anotado.
