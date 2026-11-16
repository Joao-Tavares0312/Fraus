# Conformidade regulatória — o Fraus e o EU AI Act

> Escrito em 10/09/2026, corrigido em 28/09/2026 e revisto no código em 16/11/2026.
> Este documento existe porque o Fraus **classifica emoção a partir de texto**. Ele descreve o escopo, o
> que o sistema infere, o que ele nunca decide sozinho e — a parte que virou
> regra de código — **o que ele está proibido de fazer**.

---

## 1. Por que este documento existe

`fraus/sinais/emocao.py` classifica **sete classes** — as seis emoções básicas
de Ekman mais neutro — e deriva **desprezo** da díade raiva + nojo. O Regulamento (UE) 2024/1689 define
“sistema de reconhecimento de emoções” como inferência baseada em **dados
biométricos**. O Fraus recebe texto de chat, não imagem, voz ou outro dado
biométrico; portanto não deve ser apresentado como enquadrado automaticamente
nessa definição. Ainda há obrigações de proteção de dados, transparência e
limitação de finalidade, que dependem do contexto concreto de implantação.

Esta documentação é orientação técnica, não parecer jurídico. O enquadramento
de uma implantação comercial deve ser revisto por profissional qualificado.

## 2. Escopo do sistema

| | |
|---|---|
| **O que analisa** | transcrições de atendimento por chatbot, já encerradas |
| **Sobre quem infere** | o **cliente** — e apenas o cliente |
| **O que infere** | satisfação (score 0–100 → nota 0–10 → categoria NPS), emoção por mensagem, ironia por mensagem, indicadores agregados |
| **Quando roda** | leitura retrospectiva de transcrições; o produto não emite alertas durante o atendimento. A entrada aceita `encerrada_em` ausente, portanto encerramento não é uma validação obrigatória do schema |
| **O que decide sozinho** | **nada** |
| **Base do modelo** | três BERTimbau fine-tunados + regressão logística, inferência local em CPU |

## 3. As três obrigações que já valem, e a que vem

### 3.1 Transparência como compromisso do produto

Mesmo sem afirmar o enquadramento no Art. 50(3), inferência sobre emoção não
deve ser escondida de quem é afetado nem de quem interpreta o resultado.

**O que o código oferece:** `dashboard/components/CabecasDeLeitura.tsx` traz
a etiqueta de leitura automática de emoção e explicita que ela descreve o
cliente. A ressalva depende das propriedades do componente; quando o painel
se repete por mensagem, o aviso deve ser lido no contexto da tela, não como
garantia automática de que cada número tenha texto próprio.
A obrigação de informar o cliente final é de quem opera o chatbot; exibir
uma ressalva na dashboard não demonstra que esse aviso tenha sido entregue
ao titular.

### 3.2 Limite de finalidade: não pontuar trabalhadores

O Art. 5(1)(f) proíbe determinados sistemas biométricos de inferência de emoção
no trabalho. O Fraus textual não deve reivindicar que essa proibição específica
se aplica automaticamente a ele. Ainda assim, pontuar atendentes seria uma
expansão de finalidade de alto impacto e permanece proibida por política do
produto.

> ### Regra: **o Fraus não pontua atendentes.**
>
> O atendente humano aparece no transcript — a escalação é parte do dado —,
> mas `features_texto` seleciona apenas `conversa.mensagens_cliente`;
> a atribuição por mensagem do `Motor` também reserva as cabeças para falas do cliente.
> O classificador de baixo nível recebe textos, sem conhecer o autor: a
> restrição está na seleção feita pelo pipeline, não numa recusa do modelo.
> Contagens e latências humanas descrevem a estrutura do atendimento, não o
> desempenho individual de um trabalhador. Não há tela ou rota de ranking ou
> score individual por atendente no produto revisado.
>
> Vale com o mesmo peso das invariantes do `CLAUDE.md`: implementar isso não é
> feature nova, é violação.

### 3.3 Controles recomendados para uma implantação comercial

Não se afirma aqui que o Fraus textual seja automaticamente “alto risco” pelo
Anexo III. Os controles abaixo continuam recomendados porque tratam dados de
atendimento e inferências sobre pessoas.

Onde o Fraus já está, hoje, em relação a cada uma:

| Obrigação | Estado no Fraus |
|---|---|
| **Supervisão humana** | o analista pode curar o léxico (`sinais/curadoria.py`), alterar as faixas de NPS (`PUT /configuracoes`) conforme permissão e ler transcritos. As saídas não acionam decisões sobre clientes ou trabalhadores |
| **Logging** | `entregas_webhook` registra vereditos e motivos das entregas tratadas pela rota; recusas anteriores ao handler, como validação de schema, não são promessa de registro nessa tabela. `auditoria_eventos` encadeia eventos por SHA-256, sem âncora externa contra remoção do sufixo ou reescrita integral |
| **Transparência** | etiqueta de estimativa em todo número inferido; limitações declaradas em tela e em `docs/treinamento.md` |
| **Monitoramento pós-mercado** | `GET /saude/deriva` reporta quais features estão fora da faixa de distribuição em que o modelo foi treinado |
| **Avaliação de conformidade** | não feita. É trabalho de quem for colocar isto em produção comercial, e está fora do escopo do TCC |
| **Avaliação de impacto em direitos fundamentais** | não feita, pelo mesmo motivo |

**Isto não é uma declaração de conformidade.** É um mapeamento honesto do que já
está de pé e do que não está.

## 4. Limitações que importam para quem lê um número do Fraus

- **O NPS é inferido do texto, não perguntado.** O intervalo de confiança que a
  interface mostra cobre a **incerteza amostral** — não a incerteza do modelo.
- **A cabeça de ironia não entra no vetor** desde 04/09/2026: as features
  mediram sentimento positivo no corpus do fusor da época. A cabeça continua
  obrigatória e exibida por mensagem. O registro de 13/11/2026 documenta a
  publicação da cabeça MultiPICo e melhora no teste desse corpus, não validação
  em atendimento real; ver [Novidades](novidades-2026-11-13.md).
- **O sinal de tempo é treinado em dados sintéticos**, calibrados por
  literatura, porque nenhum corpus público em português tem timestamps de
  diálogo. Desde 15/09/2026 a espera entra em `log1p` e pesa cada vez mais
  devagar (na medição histórica de 15/09, 3 h ≈ 2,1× o texto), mas espera
  fora da faixa do treino continua fora da distribuição.
  `GET /saude/deriva` torna essa extrapolação visível. No código de 13/11,
  conversa sem resposta tem latências ausentes, não zero; o fusor usa a média
  do treino, sem avaliar desempenho individual de quem atende.
- **Desprezo não é classe treinada**; é derivado da díade raiva + nojo.
- **Ausência de dado nunca vira zero.** Conversa sem fala do cliente sai "sem
  sinal", em toda superfície.
- **E2 implementado não é confiança validada.** O artefato conformal não está
  na árvore revisada; cobertura empírica não foi demonstrada. E5 usa regras,
  sem precisão/recall medidos em amostra real anotada.
- **Modelos congelados desde 16/11/2026.** A decisão de não retreinar,
  recalibrar ou promover candidatos não elimina essas limitações.

## 5. Fontes

- [Regulamento (UE) 2024/1689 — texto oficial](https://eur-lex.europa.eu/legal-content/PT/TXT/?uri=CELEX:32024R1689)
- [Art. 50 — obrigações de transparência](https://artificialintelligenceact.eu/transparency-rules-article-50/)
- [Diretrizes de transparência da Comissão Europeia](https://www.hunton.com/privacy-and-cybersecurity-law-blog/european-commission-issues-eu-ai-act-transparency-guidelines)
- [Obrigações de transparência em vigor desde 02/08/2026 — Cooley](https://www.cooley.com/news/insight/2026/2026-08-03-eu-ai-act-transparency-obligations-take-effect-2-august-2026)
- [Emotion AI de cliente vira alto risco — CX Today](https://www.cxtoday.com/contact-center/customer-emotion-ai-august-2026-compliance-cliff/)
