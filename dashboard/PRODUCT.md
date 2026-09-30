# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Analista de operação de atendimento, em português do Brasil, sentado no próprio
monitor em sala com luz normal — **uso diário, não apresentação**. Ele chega
com uma pergunta operacional ("como estamos esta semana?", "quais atendimentos
deram errado?") e precisa varrer números e descer para casos individuais.

Audiência secundária confirmada: a **banca avaliadora** do trabalho de
conclusão, que julga o rigor metodológico tanto quanto o resultado. Ela não é a
cena de uso que governa o desenho.

## Product Purpose

Medir satisfação em atendimentos por chatbot **sem perguntar nada ao cliente**.
O produto existe porque a nota declarada mente: o cliente escreve "ok, obrigado
🙂" e sai insatisfeito. Modelos que olham só características genéricas da
conversa explicam ~10% da variância da satisfação declarada.

Sucesso é o analista confiar no número o bastante para agir, sabendo com
precisão o que nele é medido e o que é estimado.

## Positioning

Fusão de **39 features, sete famílias no vetor** (oito famílias de sinal no
sistema — a ironia continua lida por mensagem, só não pontua mais) — texto
(BERTimbau fine-tunado), emoji (Emoji Sentiment Ranking, com a posição relativa
na mensagem como feature), tempo (latência como feature aprendida, não
penalidade linear), emoção (sete classes + desprezo derivado), léxico
(SentiLex-PT02, com negação), ironia (cabeça binária, exibida por mensagem mas
fora do vetor desde 04/09/2026 — vazamento de corpus medido, ver o README),
estilo (caixa alta, pontuação, alongamento, palavrão e censura) e incongruência
(polaridade
emoji×texto, marcador de contraste, hipérbole e aspas irônicas) — sem LLM
em runtime.

O que um produto vizinho não copia honestamente: a **atribuição**. Como o score
de texto é por mensagem, o produto aponta *quais falas* puxaram a nota, em vez
de devolver um número opaco.

## Operating Context

- Atendimentos entram por importação, fontes de Integrações ou análise de
  upload/conversa colada com a opção de salvar. A análise avulsa segue disponível.
- O analista filtra por período e desce da visão agregada para a transcrição de
  um atendimento.
- A API oferece autenticação JWT de usuários e credenciais técnicas. Produção
  usa PostgreSQL/Supabase; SQLite permanece para desenvolvimento e testes.
- Oito telas: Visão geral, Atendimentos, Modelo, Configurações, Integrações,
  Grafo, Analisar e Operação. A última reúne radar, equipe e escala, jornadas,
  investigações, replay, laboratório e acessos.

## Capabilities and Constraints

- Indicadores: NPS inferido, CSAT, taxa de contenção, latência mediana.
- Faixas de NPS **configuráveis** (padrão 0–6 detrator, 7–8 neutro, 9–10
  promotor) e limiares de latência de exibição (padrão 10 s / 60 s / 3 min).
- Score e categoria são **sempre derivados no servidor**; a interface nunca
  recalcula nota.
- **Sem LLM em runtime** — requisito do trabalho, não escolha de custo.
- Os artefatos treinados são obrigatórios no motor real. A gravação pela tela
  Analisar recusa motores de demonstração. Métricas ausentes ficam em estado vazio.
- O sinal de tempo é treinado em conversas sintéticas, porque nenhum corpus
  público de review PT-BR tem timestamps de diálogo.
- A classe neutra pura pontua 75 (peso 0,75 no fusor), vira nota 8 e entra
  na faixa neutra padrão. O NPS permanece uma estimativa. O intervalo usa
  AW(3,T), e o cartão respeita a decisão do servidor de ocultar o ponto
  quando há menos de 30 atendimentos com sinal.
- Série temporal, léxico por classe, tempos e notas são derivados no servidor.
- Equipes têm proprietário, gestor e membro. Convites possuem validade de uma
  a 168 horas, limite de usos e revogação. O token é guardado somente como hash.
  Cadastro por link começa sem acesso; aceitar publica filiação e escopo inicial
  na mesma transação. Política administrativa explícita vence o escopo da equipe.
- Papel global e papel na equipe são distintos: convite não concede `dev`.
  Hierarquia ausente não libera gestão; respostas incompletas têm estado de
  erro recuperável. Aceitar convite exige uma sessão de usuário válida.
- Cenários de escala e laboratório são hipóteses visíveis, nunca medidas reais.
  Antes/depois não demonstra causalidade; comparar modelos não os promove.

## Brand Commitments

- Nome **Fraus**, a divindade romana da fraude — contraparte latina de
  Ápate/Dolos, citada por Cícero entre a prole de Érebo e da Noite. O nome carrega a tese:
  o cliente mente, o texto não.
- Logo: monograma **FR**, F branco e R dourado sobre preto (`#070707`).
- Vinculante por decisão do usuário nesta sessão:
  - os **textos de honestidade** ("estimativa", "sem sinal", nota metodológica,
    estados vazios que nomeiam o que falta) permanecem;
  - o encoding **âmbar = o que foi dito / azul = o que foi medido**;
  - o **gráfico sobreposto de NPS × latência** — pode mudar de forma, mas a
    sobreposição continua, porque é o trade-off que cartão isolado esconde.

## Evidence on Hand

- Snapshot versionado de atendimentos sintéticos no banco de demonstração, incluindo
  atendimentos **sem fala do cliente** para exercitar o estado "sem sinal".
- Léxico de emoji real: 969 entradas do Emoji Sentiment Ranking, com as
  contagens de anotação humanas originais.
- Referências citáveis no repositório (Springer 2025, IJHCI 2025, Ekman 1992,
  Plutchik 1980, Cícero).
- A demonstração contém atendimentos sintéticos; uma instalação conectada recebe
  dados enviados pelo operador. Não afirmar desempenho em clientes reais sem
  validação independente. Intervalo amostral não mede erro do classificador.

## Product Principles

1. **Nunca inventar número.** Onde falta dado, a tela nomeia o que falta e qual
   etapa ou endpoint resolveria. Numa ferramenta batizada com o nome do daemon
   do engano, dado plausível inventado seria a pior falha possível.
2. **Separar o dito do medido, sempre visivelmente.** A distância entre os dois
   é a informação que o produto vende.
3. **Ausência de dado não é insatisfação.** "Sem sinal" nunca vira zero, nunca
   entra em média, e não pertence à escala.
4. **Mostrar o trade-off, não o indicador isolado.** Otimizar um KPI sozinho
   quebra outro.
5. **O servidor é a fonte da verdade.** Score e categoria vêm dele; a interface
   apresenta e não recalcula.

## Accessibility & Inclusion

- Todo par de cor que carrega **texto** cruza WCAG AA (4.5:1), verificado por
  cálculo em `npm run contraste` — cor de marcação e cor de tipo são coisas
  diferentes.
- Categoria **nunca é comunicada só por cor**: acompanha rótulo textual.
- `prefers-reduced-motion` respeitado.
- Interface inteiramente em português do Brasil.

## Open Decisions

- A comparação de fusores precisa de artefato candidato compatível configurado
  no servidor. A funcionalidade não equivale a promoção automática de modelo.
- A publicação da API é separada da dashboard. O workflow está implementado;
  seus secrets no ambiente `production-api` ainda precisam ser configurados.

- A **empresa fictícia** do trabalho não está definida (ramo, porte, canais,
  volume plausível de atendimentos). Ela atravessa a apresentação inteira e
  ainda não pode ser assumida.
