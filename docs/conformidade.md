# Conformidade regulatória — o Fraus e o EU AI Act

> Escrito em 10/09/2026. Este documento existe porque o Fraus **classifica
> emoção**, e isso tem nome no regulamento europeu. Ele descreve o escopo, o
> que o sistema infere, o que ele nunca decide sozinho e — a parte que virou
> regra de código — **o que ele está proibido de fazer**.

---

## 1. Por que este documento existe

`fraus/sinais/emocao.py` classifica **sete emoções** (as de Ekman) e deriva
**desprezo** da díade raiva + nojo. Pela letra do Regulamento (UE) 2024/1689 —
o *AI Act* — isso é um **sistema de reconhecimento de emoções**: um sistema de
IA destinado a identificar ou inferir emoções de pessoas naturais a partir de
dados biométricos ou comportamentais.

Não importa que o Fraus rode local, sem LLM e sem câmera. O que classifica o
sistema é **o que ele infere sobre pessoas**, não o tamanho do modelo.

## 2. Escopo do sistema

| | |
|---|---|
| **O que analisa** | transcrições de atendimento por chatbot, já encerradas |
| **Sobre quem infere** | o **cliente** — e apenas o cliente |
| **O que infere** | satisfação (score 0–100 → nota 0–10 → categoria NPS), emoção por mensagem, ironia por mensagem, indicadores agregados |
| **Quando roda** | em lote, sobre conversa terminada. Nunca em tempo real durante o atendimento |
| **O que decide sozinho** | **nada** |
| **Base do modelo** | três BERTimbau fine-tunados + regressão logística, inferência local em CPU |

## 3. As três obrigações que já valem, e a que vem

### 3.1 Transparência — Art. 50(3), desde 02/08/2026

O regulamento exige que o *deployer* de um sistema de reconhecimento de emoções
**informe as pessoas naturais expostas** a ele.

**Como o Fraus cumpre:** toda tela onde a leitura de emoção aparece
(`components/CabecasDeLeitura.tsx`, compartilhado pelo simulador e pela análise)
carrega a etiqueta de exposição, em linguagem de gente, junto da nota
metodológica que já qualificava o NPS como inferido. A obrigação de *informar o
cliente final* é de quem opera o chatbot — o Fraus fornece o texto e diz que ela
existe; ele não fala com o cliente.

### 3.2 Proibição no local de trabalho — desde 02/02/2025

Reconhecimento de emoção **no ambiente de trabalho é proibido**, sem exceção
comercial. Isso não é obrigação a cumprir: é uma fronteira que o produto não
pode cruzar.

> ### Regra: **o Fraus não pontua atendentes.**
>
> O atendente humano aparece no transcript — a escalação é parte do dado — e o
> classificador de texto **recusa pontuar mensagem que não seja do cliente**
> (`sinais/texto.py`; `qtd_humano` e `latencia_mediana_humano_s` são contagem e
> relógio, nunca julgamento). "Score de performance por atendente" é a sugestão
> mais recorrente em analytics de atendimento, e no Fraus ela está **fechada
> por desenho**, não esquecida no backlog.
>
> Vale com o mesmo peso das invariantes do `CLAUDE.md`: implementar isso não é
> feature nova, é violação.

### 3.3 Alto risco (Anexo III) — aplicação em 02/12/2027

Reconhecimento de emoção voltado ao **cliente** é permitido, mas reclassificado
como alto risco, com obrigações que entram em 02/12/2027: avaliação de
conformidade, supervisão humana, logging, avaliação de impacto em direitos
fundamentais e monitoramento pós-mercado.

Onde o Fraus já está, hoje, em relação a cada uma:

| Obrigação | Estado no Fraus |
|---|---|
| **Supervisão humana** | o sistema não decide nada. O analista curou o léxico (`sinais/curadoria.py`), move as faixas de NPS (`PUT /configuracoes`) e lê os transcritos. Nenhuma saída aciona ação automática sobre ninguém |
| **Logging** | `entregas_webhook` registra toda entrega e toda recusa, com veredito e motivo. É o embrião da trilha de auditoria |
| **Transparência** | etiqueta de estimativa em todo número inferido; limitações declaradas em tela e em `docs/treinamento.md` |
| **Monitoramento pós-mercado** | `GET /saude/deriva` reporta quais features estão fora da faixa de distribuição em que o modelo foi treinado |
| **Avaliação de conformidade** | não feita. É trabalho de quem for colocar isto em produção comercial, e está fora do escopo do TCC |
| **Avaliação de impacto em direitos fundamentais** | não feita, pelo mesmo motivo |

**Isto não é uma declaração de conformidade.** É um mapeamento honesto do que já
está de pé e do que não está.

## 4. Limitações que importam para quem lê um número do Fraus

- **O NPS é inferido do texto, não perguntado.** O intervalo de confiança que a
  interface mostra cobre a **incerteza amostral** — não a incerteza do modelo.
- **A cabeça de ironia é pouco confiável** e por isso **não pontua** desde
  04/09/2026: no corpus de treino ela funciona como detector de sentimento
  positivo. Continua sendo exibida, com a ressalva colada.
- **O sinal de tempo é treinado em dados sintéticos**, calibrados por
  literatura, porque nenhum corpus público em português tem timestamps de
  diálogo. Fora da faixa de latência do treino, o relógio domina a nota — é
  limitação medida e declarada, e `GET /saude/deriva` a torna visível.
- **Desprezo não é classe treinada**; é derivado da díade raiva + nojo.
- **Ausência de dado nunca vira zero.** Conversa sem fala do cliente sai "sem
  sinal", em toda superfície.

## 5. Fontes

- [Regulamento (UE) 2024/1689 — AI Act](https://artificialintelligenceact.eu/)
- [Art. 50 — obrigações de transparência](https://artificialintelligenceact.eu/transparency-rules-article-50/)
- [Diretrizes de transparência da Comissão Europeia](https://www.hunton.com/privacy-and-cybersecurity-law-blog/european-commission-issues-eu-ai-act-transparency-guidelines)
- [Obrigações de transparência em vigor desde 02/08/2026 — Cooley](https://www.cooley.com/news/insight/2026/2026-08-03-eu-ai-act-transparency-obligations-take-effect-2-august-2026)
- [Emotion AI de cliente vira alto risco — CX Today](https://www.cxtoday.com/contact-center/customer-emotion-ai-august-2026-compliance-cliff/)
