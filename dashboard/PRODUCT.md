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

Estimar satisfação em atendimentos por chatbot **sem perguntar nada ao cliente**.
Um encerramento como "ok, obrigado 🙂" não basta para concluir satisfação ou
insatisfação; o contexto pode trazer sinais diferentes. No estudo Springer 2025
citado no projeto, variáveis genéricas explicaram cerca de 10% da variância da
satisfação declarada, e variáveis de domínio elevaram esse valor a cerca de 27%.
Esses resultados não medem desempenho do Fraus nem estabelecem um teto universal.

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

A **inspeção da leitura** separa dois objetos: probabilidades do classificador
de texto por mensagem e contribuições das features no fusor. O destaque de uma
fala mostra inclinação textual, não sua causa ou efeito isolado sobre a nota.
As contribuições são termos na diferença entre logits de satisfeito e
insatisfeito, não pontos da nota; a transformação em score é não linear.

## Operating Context

- Atendimentos entram pela tela Analisar (solta o arquivo, salva direto quando
  a leitura é confiável) ou sozinhos pelas fontes de Integrações — o Tars
  conecta em dois cliques. A importação por pasta do servidor saiu da tela.
  O resultado prioriza confirmação de gravação, resumo e conversa; inspeção
  técnica fica disponível sem competir com essa leitura.
- O analista filtra por datas ou pelos atalhos de 7 dias, 30 dias e todo o
  período, ancorados no último dia com dados. O período ativo acompanha a
  navegação da visão agregada para os atendimentos.
- Sem histórico disponível, a tela orienta ao primeiro arquivo e oferece
  integração só a quem pode configurá-la. Um filtro sem resultados oferece
  limpar período; uma API indisponível continua sendo erro, não banco vazio.
- A API oferece autenticação JWT de usuários e credenciais técnicas. Produção
  usa PostgreSQL/Supabase; SQLite permanece para desenvolvimento e testes.
- Oito telas. Na lateral, o dia a dia: Visão geral, Atendimentos, Analisar,
  Grafo e Modelo (dev). No menu da conta: Operação (radar, equipe e escala,
  jornadas, investigações, replay, laboratório e acessos), Integrações e
  Configurações.

## Capabilities and Constraints

- Indicadores: NPS inferido, CSAT, taxa de contenção, latência mediana.
- Faixas de NPS **configuráveis** (padrão 0–6 detrator, 7–8 neutro, 9–10
  promotor) e limiares de latência de exibição (padrão 10 s / 60 s / 3 min).
- Score e categoria são **sempre derivados no servidor**; a interface nunca
  recalcula nota.
- **Sem LLM em runtime** — a inferência roda em CPU e não envia conversas a APIs
  de LLM. Isso não é garantia universal sobre hospedagem, armazenamento ou transporte.
- **Não pontuar atendentes é política firme do produto.** A definição de
  reconhecimento de emoção do EU AI Act exige dados biométricos; classificação
  textual não implica enquadramento automático nessa definição.
- Os artefatos treinados são obrigatórios no motor real. A gravação pela tela
  Analisar recusa motores de demonstração. Métricas ausentes ficam em estado vazio.
- O sinal de tempo é treinado em conversas sintéticas, porque nenhum corpus
  público de review PT-BR tem timestamps de diálogo.
- A classe neutra pura pontua 75 (peso 0,75 no fusor), vira nota 8 e entra
  na faixa neutra padrão. O NPS permanece uma estimativa. O intervalo usa
  AW(3,T) e mede incerteza amostral, não erro do classificador. O cartão oculta
  o ponto com menos de 30 atendimentos com sinal. Latência e contenção são observadas;
  não há promessa de intervalo em todo indicador.
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
  Ápate/Dolos, citada por Cícero entre a prole de Érebo e da Noite. O nome remete
  à diferença possível entre a cortesia do encerramento e os sinais do contexto,
  não à certeza de que o cliente mente ou de que o texto revela seu estado real.
- Logo: monograma **FR**, F branco e R dourado sobre preto (`#070707`).
- Vinculante por decisão do usuário nesta sessão:
  - os **textos de honestidade** ("estimativa", "sem sinal", nota metodológica,
    estados vazios que nomeiam o que falta) permanecem;
  - o encoding **âmbar = dito / azul = medido nas marcas gráficas**; desde
    22/10/2026, textos de medidas usam branco mineral no escuro e grafite no claro;
  - o **gráfico sobreposto de NPS × latência** — pode mudar de forma, mas a
    sobreposição continua, porque é o trade-off que cartão isolado esconde.
  - o **FR escultórico**, derivado do monograma oficial, a tipografia quadrada
    Chakra Petch e o fundo de pincel em toda a LP (direção aprovada em 16/10/2026);
  - dashboard calma, com tema escuro padrão e alternativa clara; a LP e o acesso
    permanecem escuros sem apagar a preferência da ferramenta;
  - a marca não pode custar cinco malhas escondidas: mobile, movimento reduzido
    e backend gráfico de software usam a mesma arte pré-renderizada; desktop
    com contexto elegível monta uma única escultura, sem loop ocioso.

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
- Na LP, só há análises quando o snapshot validado foi gravado pelo motor real.
  Sem ele, a página oferece método e limites, sem resultados ou escolha fictícia.
  A procedência registra data, API e hash parcial das importâncias do fusor;
  esse hash não identifica os checkpoints nem o pipeline completo.

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
6. **Brincadeira não falsifica dado.** A Fraus-chan escondida na marca usa
   artes e falas fixas. Não lê conversas, altera indicadores nem pontua o usuário.

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
