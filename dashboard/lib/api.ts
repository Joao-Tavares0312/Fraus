/**
 * Cliente da API do Fraus.
 *
 * Toda leitura e `no-store`: a dashboard e um instrumento de leitura de um
 * banco que muda a cada importacao, e um numero em cache seria um numero
 * errado apresentado com confianca.
 *
 * Nenhuma funcao daqui lanca para o chamador de pagina: elas devolvem
 * `Resultado<T>`, para que a falha de UM bloco nao derrube os outros -- regra
 * de produto 5 (se um indicador falha, so o card dele mostra falha).
 */

/**
 * O caminho do proxy no servidor Next. E o destino das chamadas feitas PELO
 * NAVEGADOR: o proxy anexa a chave de acesso (FRAUS_CHAVE_ACESSO, env
 * server-side) e repassa para FRAUS_API_URL, de modo que a chave nunca chega
 * ao bundle.
 */
const PROXY = "/api/fraus";

/**
 * Destino de UMA chamada, escolhido pelo lado em que este codigo roda.
 *
 * No SERVIDOR (Server Components, que sao a maioria das telas) a URL precisa
 * ser absoluta: o `fetch` do Node recusa caminho relativo -- nao existe
 * "origem da pagina" ali. Passar `/api/fraus` derrubava TODA tela renderizada
 * no servidor com um TypeError que `proteger` engolia e virava estado de erro.
 * E dar a volta pelo proxy seria absurdo de qualquer modo: o processo falaria
 * consigo mesmo para chegar na API que ele ja alcanca direto.
 *
 * No NAVEGADOR o destino e o proxy, justamente para a chave nao sair do
 * servidor.
 */
function noServidor(): boolean {
  return typeof window === "undefined";
}

export function urlDaApi(rota: string): string {
  if (!noServidor()) return `${PROXY}${rota}`;
  return `${process.env.FRAUS_API_URL ?? "http://localhost:8000"}${rota}`;
}

/**
 * Cabecalhos da chamada, incluindo a autorizacao quando falamos direto com a
 * API (server-side). No navegador nao ha o que anexar: quem autentica e o
 * proxy.
 *
 * A resolucao de credencial (ambiente, cookie de quem ligou pela tela, ou o
 * arquivo que a API escreve na primeira subida) mora em
 * `lib/credencial-do-servidor.ts`, NUNCA aqui -- e so chegada por `import()`
 * DINAMICO, dentro do `if (noServidor())`. Este arquivo e importado por
 * componentes de CLIENTE (o simulador, a tela de autenticacao, a de
 * integracoes -- `grep -rn "from \"@/lib/api\"" components`), entao vai para
 * o bundle do navegador. Um `import` estatico do modulo de credencial
 * arrastaria `node:fs` e `next/headers` para esse bundle e quebraria o build
 * do lado do cliente. O `import()` dinamico so resolve o modulo fisicamente
 * quando o ramo roda -- e esse ramo so roda no servidor, entao o navegador
 * nunca pede esse chunk.
 */
export async function cabecalhosDaApi(
  extras?: Record<string, string>,
): Promise<Record<string, string>> {
  const cabecalhos: Record<string, string> = { ...(extras ?? {}) };
  if (noServidor()) {
    const { autorizacaoDoServidorAtual } = await import("./credencial-do-servidor");
    const autorizacao = await autorizacaoDoServidorAtual();
    if (autorizacao) cabecalhos["Authorization"] = autorizacao;
  }
  return cabecalhos;
}

/**
 * O endereco da API para MOSTRAR no exemplo de `curl` da tela de integracoes
 * -- nunca destino de fetch. Quem le esse exemplo e um integrador externo,
 * que fala com a API direto (nao com o proxy, que so existe para o navegador
 * desta dashboard).
 *
 * So pode ser chamada NO SERVIDOR, e e o ponto todo: antes isto era uma
 * constante lida de `NEXT_PUBLIC_API_URL`, uma SEGUNDA fonte de verdade para
 * um endereco que `FRAUS_API_URL` ja definia. Com as duas existindo, um deploy
 * que configurasse so a segunda continuava ensinando `localhost:8000` ao
 * integrador -- um comando errado, exibido com confianca, sem nada na tela
 * reclamando. Uma variavel so, lida onde ela existe, e a resposta desce por
 * prop ate o componente que a imprime.
 */
export function baseDaApi(): string {
  return process.env.FRAUS_API_URL ?? "http://localhost:8000";
}

export type Categoria = "detrator" | "neutro" | "promotor";

export type IntervaloNps = {
  nps: number | null;
  ic_inferior: number;
  ic_superior: number;
  n: number;
};

export type Indicadores = {
  /** null quando nenhum atendimento tem score: ausencia de dado nao e zero. */
  nps: number | null;
  /**
   * O mesmo NPS com a incerteza AMOSTRAL: ponto, as duas pontas do intervalo
   * de 95% e o n. `nps` DENTRO do intervalo vem null quando a amostra e
   * pequena demais para um ponto estimado -- e o `n` vem preenchido mesmo
   * assim, para a tela dizer quanto falta.
   *
   * Opcional porque uma API anterior a este campo nao o devolve.
   */
  nps_intervalo?: IntervaloNps | null;
  /** null quando nenhum atendimento tem score. */
  csat: number | null;
  /**
   * Contencao NAO depende de score: conversa sem fala do cliente nao tem NPS
   * nem CSAT e mesmo assim conta como contida. So o conjunto VAZIO vem
   * `null` -- nao houve o que conter.
   */
  containment_rate: number | null;
  /**
   * Percentual dos atendimentos CONTIDOS que sairam detratores -- o sucesso
   * falso. `null` quando nenhum contido tem score, nunca 0.
   *
   * Opcional porque uma API anterior a este indicador nao o devolve, e
   * `undefined` ali significa "nao sei", que nao pode virar zero.
   */
  falso_containment?: number | null;
  /** Denominador do campo acima -- a tela diz "3 de 12", nao so o percentual. */
  contidos_com_score?: number;
  total_conversas: number;
  sem_sinal: number;
  /**
   * Mediana das esperas cliente -> resposta do recorte, derivada dos
   * timestamps na leitura. null sem nenhum par -- nunca zero.
   */
  tempo_mediano_resposta_s: number | null;
  /**
   * Quantas conversas do BANCO INTEIRO foram pontuadas com uma versao anterior
   * do lexico curado, e o total. As duas ignoram `de`/`ate` de proposito: a
   * regua misturada e propriedade do banco, nao do recorte que se olha.
   *
   * Opcionais porque uma API anterior a este mecanismo nao as devolve -- e
   * `undefined` ali significa "nao sei", que nao pode virar zero.
   */
  pontuadas_com_lexico_antigo?: number;
  /**
   * A mesma contagem somando troca de MODELO (retreino do fusor, regra da
   * cortesia), desde 15/09/2026. E a que o aviso usa; a de lexico continua
   * existindo com o sentido de sempre.
   */
  pontuadas_com_regua_antiga?: number;
  total_no_banco?: number;
};

/**
 * Quando o tempo contesta o elogio.
 *
 * Score saturado convivendo com espera longa: a leitura mais provavel e ironia
 * ("que atendimento maravilhoso, so esperei 3 horas"), e o modelo nao alcanca
 * isso -- nenhuma feature agregada de conversa reverte uma probabilidade
 * saturada por mensagem.
 *
 * ELA MARCA, NAO CORRIGE. `score`, `nota` e `categoria` do mesmo objeto
 * continuam valendo e o atendimento continua contando no NPS. Se um dia este
 * tipo ganhar `nota` ou `categoria`, alguem vai le-las em vez das derivadas de
 * verdade, e a regua do NPS passa a ter duas fontes.
 *
 * Os quatro numeros vem do servidor de proposito: a frase de tela e montada a
 * partir deles, e redigitar `score > 95` aqui seria a regra derivada duplicada
 * no cliente que ja custou divergencia de arredondamento neste projeto.
 * Derivada em `fraus/contestacao.py`; desenho em
 * `docs/superpowers/specs/2026-09-08-abstencao-por-contestacao-design.md`.
 */
export type Contestacao = {
  motivo: "elogio_contra_espera";
  score: number;
  limiar_score: number;
  latencia_mediana_s: number;
  limiar_s: number;
};

export type ResumoConversa = {
  id: string;
  canal: string;
  iniciada_em: string;
  score: number | null;
  categoria: Categoria | null;
  /**
   * Nota 0-10 DERIVADA NO SERVIDOR a partir do score. A dashboard nunca
   * recalcula: o arredondamento do Python (bancario) e o do JavaScript
   * (meio para cima) divergem nas fronteiras 6/7 e 8/9, e a fonte da verdade
   * e o servidor -- ele e quem grava a categoria.
   */
  nota: number | null;

  /**
   * Ficha operacional derivada pelo servidor em `fraus.resumo`.
   *
   * Os tempos vem `null` -- nunca `0` -- quando a espera nao existiu. Zero
   * numa coluna de tempo de resposta se le como "respondeu na hora", e uma
   * conversa que nunca teve atendente humano apareceria como a mais agil da
   * operacao. Toda exibicao daqui precisa tratar o nulo como "não houve".
   */
  qtd_mensagens: number;
  qtd_cliente: number;
  qtd_bot: number;
  qtd_humano: number;
  latencia_primeira_resposta_s: number | null;
  latencia_mediana_s: number | null;
  latencia_mediana_bot_s: number | null;
  latencia_mediana_humano_s: number | null;
  duracao_s: number;
  escalou_para_humano: boolean;
  encerrada_em: string | null;
  desfecho: Desfecho;

  /** `null` na esmagadora maioria dos atendimentos -- ver `Contestacao`. */
  contestacao: Contestacao | null;

  /**
   * POR QUE nao ha nota, derivado no servidor (`Conversa.motivo_sem_sinal`).
   * `null` quando ha. "so_cortesia" existe desde 15/09/2026: o cliente falou,
   * mas so "ok, obrigado" -- e a tela nao pode dizer que ele nao falou.
   */
  motivo_sem_sinal: MotivoSemSinal | null;

  /**
   * Tem score, e pouca fala do cliente para sustenta-lo -- a CABECA
   * TRACEJADA. `null` quando nao ha fala nenhuma: ai o estado e "sem sinal",
   * que tem forma propria (a cabeca vazada), e confundir os dois perderia a
   * distincao que o produto inteiro defende.
   *
   * Derivada no SERVIDOR a partir de evidencia OBSERVAVEL (quantas mensagens,
   * quantas palavras), nunca da probabilidade do modelo -- probabilidade nao
   * calibrada nao e confianca. Por isso o campo nao se chama `confianca`.
   *
   * Opcionais: uma API anterior a este campo nao os devolve.
   */
  evidencia_fraca?: boolean | null;
  motivos_evidencia_fraca?: string[];
};

/**
 * Como o atendimento terminou. Conjunto FECHADO e cada um verificavel no dado
 * -- nao existe "resolvida", porque resolucao e julgamento sobre o problema do
 * cliente e nada no dado a sustenta. A precedencia esta em `fraus.resumo`.
 */
export type Desfecho =
  | "sem_sinal"
  | "escalada"
  | "sem_resposta"
  | "encerrada"
  | "em_aberto";

export type Autor = "cliente" | "bot" | "humano";

export type Mensagem = {
  autor: Autor;
  texto: string;
  enviada_em: string;
};

export type DetalheConversa = ResumoConversa & {
  mensagens: Mensagem[];
};

/**
 * Uma mensagem da transcricao com a probabilidade que o classificador de
 * texto deu a ela.
 *
 * Os tres campos vem `null` para bot e humano: o classificador foi treinado
 * em fala de CLIENTE, e o servidor recusa pontuar o resto. O `indice` e a
 * posicao na mesma lista de `/conversas/{id}`, para alinhar sem recontar.
 */
export type MensagemAtribuida = {
  indice: number;
  autor: Autor;
  texto: string;
  prob_insatisfeito: number | null;
  prob_neutro: number | null;
  prob_satisfeito: number | null;

  /**
   * As duas cabecas de LEITURA POR FRASE. A media de `emocao` por conversa
   * entra no vetor do fusor desde 21/08/2026 (`emocao_*`) -- o numero aqui e
   * desta frase, nao a media que pesa na nota. `prob_ironia` NAO entra mais no
   * vetor desde 04/09/2026 (`ironia_prob_media`/`ironia_prob_max` saíram de
   * `NOMES_FEATURES` -- medida no corpus de treino, a cabeca funciona como
   * detector de sentimento positivo, nao de ironia): `sinais_fora_do_score`
   * volta a trazer `["prob_ironia"]`. A interface mantem os numeros
   * visualmente separados da nota -- "ironia 0,99" encostado num score baixo
   * convida a conclusao de que esta frase causou a nota, e isso deixou de ser
   * verdade para a ironia especificamente.
   *
   * `null` quando o servidor subiu sem a cabeca correspondente.
   *
   * RESSALVA MEDIDA sobre `prob_ironia`: o modelo acerta o caso de manual
   * ("que atendimento maravilhoso, so esperei 3 horas") e marca 6 em 10 falas
   * sinceras de atendimento como ironicas. Exibir como indicio, nunca como
   * veredito. Ver tests/test_ironia_dominio.py.
   */
  emocao: Record<string, number> | null;
  prob_ironia: number | null;

  /**
   * A FORMA da escrita desta fala -- caixa alta, alongamento, enfase,
   * palavrao. Determinista, calculada por regra em `fraus/sinais/estilo.py`,
   * nao modelo -- por isso nao carrega ressalva de confiabilidade.
   *
   * `null` quando o servidor subiu sem essa cabeca (resposta de API mais
   * antiga, ou motor dublê). Nao confundir com "tudo falso": ausencia de
   * medida nao e medida negativa (invariante 2).
   */
  estilo: {
    caixa_alta: boolean;
    alongamento: boolean;
    pontuacao_enfatica: number;
    /** Intensidade do pior palavrao da fala, ou null se nao houve. */
    palavrao: number | null;
    palavrao_dirigido: boolean;
    censura: boolean;
  } | null;
};

/** Resposta de `GET /conversas/{id}/atribuicao`. */
export type Atribuicao = {
  conversa_id: string;
  /** Os mesmos score/nota/categoria de `/conversas/{id}`: gravados na importacao. */
  score: number | null;
  nota: number | null;
  categoria: Categoria | null;
  mensagens: MensagemAtribuida[];
  /** Peso absoluto GLOBAL de cada uma das 39 features do vetor do fusor --
   * aprendido no treino, nao especifico desta conversa. */
  importancias: Record<string, number>;
  /** Quanto cada feature pesou NESTA conversa: positivo empurrou para
   * satisfeito, negativo para insatisfeito. `null` quando nao ha fala do
   * cliente -- sem score, sem contribuicao. */
  contribuicoes: Record<string, number> | null;
  /**
   * Sinais que o servidor mediu mas que NAO entram no score -- hoje
   * `["prob_ironia"]`. A cabeca de ironia continua carregada e aparece por
   * mensagem em `mensagens[].prob_ironia`, mas desde 04/09/2026 nao pesa mais
   * em `contribuicoes` nem em `importancias` (medida no corpus de treino, ela
   * funciona como detector de sentimento positivo, nao de ironia). Lista
   * vazia entre 21/08/2026 e 03/09/2026, quando a ironia pontuava.
   */
  sinais_fora_do_score: string[];
};

/** Metricas do treino, exportadas pelo notebook 01. `null` ate o treino rodar. */
export type MetricasTreino = {
  acuracia?: number;
  f1_macro?: number;
  [chave: string]: unknown;
};

/**
 * Uma das tres cabecas BERTimbau, com o que o treino dela mediu.
 *
 * As metricas tem FORMATOS DIFERENTES de proposito -- cada notebook exporta o
 * que faz sentido para a sua tarefa, e uniformizar apagaria justamente os
 * campos que carregam a ressalva (o F1 em corpus independente da emocao, a
 * limitacao declarada da ironia). A tela le os campos conhecidos e mostra o
 * resto como veio.
 */
export type CabecaDeModelo = {
  nome: string;
  classes: string[];
  /** `null` antes do notebook exportar. Nunca zero. */
  metricas: MetricasTreino | null;
  /** Se ela entra no fusor. O campo existe para o caso mudar de novo; hoje as
   * tres cabecas valem `true`. */
  pontua: boolean;
};

/** Resposta de `GET /modelo` -- a ficha do modelo. */
export type FichaModelo = {
  /** Peso GLOBAL de cada uma das 35 features. Nao e especifico de conversa. */
  importancias: Record<string, number>;
  /** `null` enquanto o notebook 01 nao exportou metricas.json. NUNCA zero. */
  metricas: MetricasTreino | null;
  classes: string[];
  /**
   * As tres cabecas fine-tunadas, cada uma com a metrica que ELA mediu.
   *
   * `pontua` diz se a cabeca entra no fusor -- hoje as tres valem `true`. O
   * campo existe para o caso deixar de ser unanime de novo, e nao porque
   * separa alguma hoje.
   */
  cabecas: CabecaDeModelo[];
  /** Faixas de NPS lidas do SERVIDOR (fonte unica), nao digitadas no front. */
  faixas_nps: Record<string, [number, number]>;
  total_emojis_lexicon: number;
};

export type ItemLexicon = {
  emoji: string;
  score: number;
  negativo: number;
  neutro: number;
  positivo: number;
};

export type PaginaLexicon = {
  total: number;
  itens: ItemLexicon[];
};

export type EmojiDetectado = {
  emoji: string;
  score: number;
  /** Posicao do emoji no texto, em [0, 1]: 1 = no fim da frase. */
  posicao_relativa: number;
};

/** Resposta de `POST /modelo/simular`. */
export type Simulacao = {
  texto: string;
  prob_insatisfeito: number;
  prob_neutro: number;
  prob_satisfeito: number;
  emojis: EmojiDetectado[];
  /**
   * As oito emocoes: as sete treinadas (Ekman + neutro) mais o `desprezo`,
   * DERIVADO da diade raiva+nojo por media geometrica (Plutchik 1980) porque
   * nenhum corpus PT-BR o anota. `null` se a API subiu sem essa cabeca.
   */
  emocao: Record<string, number> | null;
  /** Ver a ressalva medida em `MensagemAtribuida.prob_ironia`. */
  prob_ironia: number | null;
  /** Ver `MensagemAtribuida.estilo`. */
  estilo: {
    caixa_alta: boolean;
    alongamento: boolean;
    pontuacao_enfatica: number;
    palavrao: number | null;
    palavrao_dirigido: boolean;
    censura: boolean;
  } | null;
};

export type SimulacaoIroniaLaya = {
  texto: string;
  classe: "nao-ironico" | "ironico";
  prob_nao_ironico: number;
  prob_ironia: number;
  modelo: string;
  checkpoint: string;
  revisao: string;
  pontua: false;
};

/**
 * Configuracao vigente e a de FABRICA, como `GET /configuracoes` devolve.
 *
 * As duas vem juntas de proposito: sem a de fabrica, "voltar ao padrao" seria
 * um botao preenchido com numeros digitados de novo na interface -- e faixa
 * duplicada em dois lugares ja foi defeito deste projeto uma vez.
 */
export type ValoresConfiguracao = {
  /** categoria -> [nota minima, nota maxima], inclusive nas duas pontas. */
  faixas_nps: Record<string, [number, number]>;
  /** [pico, saudavel, degradando] em segundos, estritamente crescentes. */
  limiares_latencia_s: number[];
};

export type Configuracoes = {
  vigente: ValoresConfiguracao;
  fabrica: ValoresConfiguracao;
};

/** Fonte de integracao. `variavel_segredo` e o NOME de uma variavel de ambiente. */
export type FonteIntegracao = {
  id: number;
  nome: string;
  canal: string;
  tipo: string;
  /** NOME da variavel de ambiente que carrega a credencial -- nunca o valor. */
  variavel_segredo: string | null;
  ativa: boolean;
  criada_em: string;
  /**
   * Os quatro ultimos caracteres da chave em uso, ou `null` se a fonte ainda
   * nao tem chave. Serve para o operador reconhecer QUAL chave esta valendo
   * ("termina em 3f9a") sem que o pedaco exibido ajude a adivinhar o resto.
   * O hash da chave nunca sai da API.
   */
  chave_dica: string | null;
  chave_criada_em: string | null;
  /**
   * Se a variavel nomeada acima EXISTE no ambiente da API, verificado na
   * leitura. `false` nao diz que o segredo esta errado: diz que a variavel
   * nao esta definida onde a API roda.
   */
  configurada: boolean;
};

export type MotivoRejeicao = {
  numero_linha: number;
  motivo: string;
};

/** Uma linha do historico de `GET /integracoes/importacoes`. */
export type Importacao = {
  id: number;
  ocorrida_em: string;
  arquivo: string;
  aceitas: number;
  rejeitadas: number;
  /** Ate 20 motivos por importacao — a API trunca; o resto fica no CSV. */
  motivos: MotivoRejeicao[];
};

export type Resultado<T> =
  | { ok: true; dado: T }
  | { ok: false; erro: string };

/*
 * TETOS DE ESPERA. Sem eles, `fetch` no servidor espera indefinidamente: uma
 * API que aceita a conexao e nunca responde -- o modo de falha que esta
 * instalacao de fato teve, com o processo vivo, a porta aberta e nenhuma
 * resposta em 60 s -- prendia o render inteiro, e o tratamento de erro do
 * projeto (`proteger`) nunca chegava a rodar. Pior que um erro na tela: uma
 * tela que nunca chega.
 *
 * A leitura tem o teto mais curto porque a pagina inteira espera por ela. A
 * escrita e mais tolerante: ela ja e uma acao explicita de quem opera, com
 * botao em estado de espera. E o upload de analise e a excecao larga --
 * inferencia de BERTimbau em CPU mediu 21,8 s para um arquivo no teto, entao
 * um teto curto ali recusaria trabalho legitimo.
 */
const ESPERA_LEITURA_MS = 15_000;
const ESPERA_ESCRITA_MS = 30_000;
const ESPERA_ANALISE_MS = 120_000;

/**
 * Status que so podem ter vindo do PROXY, nunca da API do Fraus.
 *
 * A API nao emite nenhum deles: o unico 5xx que ela produz e o 503 de
 * `/auth/entrar` sem `FRAUS_JWT_SEGREDO`, que e falha de CONFIGURACAO e tem de
 * continuar dizendo isso. Ja um 502 ou 504 significa que o tunel/proxy nao
 * conseguiu falar com a API -- ou seja, exatamente "API fora do ar", que a tela
 * so reconhecia por `ECONNREFUSED`. Publicada por tunel, a API caida passou a
 * chegar como 502, e a tela mostrava "/conversas respondeu 502" no lugar da
 * regua que ensina a levantar a API.
 *
 * 52x sao do Cloudflare, pelo mesmo motivo (523 "origin is unreachable", 524
 * "a timeout occurred").
 */
const STATUS_DE_PROXY = new Set([502, 504, 521, 522, 523, 524]);

function falhouNoProxy(status: number): boolean {
  return STATUS_DE_PROXY.has(status);
}

async function buscar<T>(rota: string): Promise<T> {
  const resposta = await fetch(urlDaApi(rota), {
    cache: "no-store",
    headers: await cabecalhosDaApi(),
    signal: AbortSignal.timeout(ESPERA_LEITURA_MS),
  });
  if (falhouNoProxy(resposta.status)) {
    throw new Error(`${MARCA_API_FORA} ${urlDaApi("")}`);
  }
  if (!resposta.ok) throw new Error(`${rota} respondeu ${resposta.status}`);
  return (await resposta.json()) as T;
}

/**
 * Escrita na API, preservando a MENSAGEM do servidor.
 *
 * O `400` do Fraus nomeia o problema ("buraco entre detrator e neutro: nenhuma
 * faixa cobre a nota 6"). Trocar isso por "erro ao salvar" jogaria fora a
 * unica frase da tela que diz o que consertar -- entao o `detail` sobe inteiro.
 */
async function escrever<T>(
  rota: string,
  metodo: "POST" | "PUT" | "PATCH" | "DELETE",
  corpo?: unknown,
): Promise<T> {
  const resposta = await fetch(urlDaApi(rota), {
    method: metodo,
    headers: await cabecalhosDaApi(
      corpo === undefined ? undefined : { "Content-Type": "application/json" },
    ),
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
    cache: "no-store",
    signal: AbortSignal.timeout(ESPERA_ESCRITA_MS),
  });

  if (falhouNoProxy(resposta.status)) {
    // Antes do `!ok`: o corpo de um 502 e HTML do proxy, e `detail` nao existe
    // nele -- a mensagem sairia como "PUT /configuracoes respondeu 502".
    throw new Error(`${MARCA_API_FORA} ${urlDaApi("")}`);
  }
  if (!resposta.ok) {
    const dado = (await resposta.json().catch(() => null)) as
      | { detail?: unknown }
      | null;
    const detalhe = dado?.detail;
    throw new Error(
      typeof detalhe === "string"
        ? detalhe
        : detalhe
          ? JSON.stringify(detalhe)
          : `${metodo} ${rota} respondeu ${resposta.status}`,
    );
  }

  if (resposta.status === 204) return undefined as T;
  return (await resposta.json()) as T;
}

/**
 * A frase de falha de CONEXAO -- a API nao esta no ar.
 *
 * Constante porque duas partes da interface precisam reconhece-la: a mensagem
 * em si, e o estado vazio, que encurta a propria prosa quando a causa e esta
 * (a regua no topo da tela ja carrega a instrucao e a acao, e repetir a
 * instrucao em cada painel e ruido, nao reforco).
 */
const MARCA_API_FORA = "API não respondeu em";

/**
 * A explicação de um estado vazio vem de a API estar fora do ar?
 *
 * `includes` e nao `startsWith`: quem monta a explicacao costuma prefixar o
 * proprio contexto ("Não foi possível listar os atendimentos: API não
 * respondeu em …"), e um detector ancorado no inicio deixava justamente essas
 * passarem -- o painel da serie continuava com o paragrafo inteiro ao lado de
 * um painel vizinho ja encurtado.
 */
export function ehFalhaDeConexao(explicacao: string): boolean {
  return explicacao.includes(MARCA_API_FORA);
}

function mensagemDeErro(erro: unknown): string {
  // Estouro de teto de espera. O `AbortSignal.timeout` levanta um
  // `TimeoutError`, e a frase que ele merece e literalmente a marca que ja
  // existe: a API nao respondeu. `AbortError` entra junto porque o Node usa um
  // ou outro conforme a versao, e distinguir os dois aqui nao muda nada para
  // quem le a tela.
  if (
    erro instanceof DOMException &&
    (erro.name === "TimeoutError" || erro.name === "AbortError")
  ) {
    return `${MARCA_API_FORA} ${urlDaApi("")}`;
  }
  if (erro instanceof Error) {
    // `fetch` recusado dá "fetch failed" — inútil para quem está na banca.
    if (/fetch failed|ECONNREFUSED|aborted|timeout/i.test(erro.message)) {
      return `${MARCA_API_FORA} ${urlDaApi("")}`;
    }
    return erro.message;
  }
  return "falha desconhecida ao consultar a API";
}

async function proteger<T>(promessa: Promise<T>): Promise<Resultado<T>> {
  try {
    return { ok: true, dado: await promessa };
  } catch (erro) {
    return { ok: false, erro: mensagemDeErro(erro) };
  }
}

/**
 * `?de=&ate=` (AAAA-MM-DD, pontas inclusivas) para as rotas que recortam no
 * servidor. Ponta ausente fica fora da query -- a API trata ausencia como
 * "sem corte", e mandar string vazia viraria 400.
 */
function queryDePeriodo(de?: string | null, ate?: string | null): string {
  const consulta = new URLSearchParams();
  if (de) consulta.set("de", de);
  if (ate) consulta.set("ate", ate);
  const texto = consulta.toString();
  return texto ? `?${texto}` : "";
}

export const obterIndicadores = (de?: string | null, ate?: string | null) =>
  proteger(buscar<Indicadores>(`/indicadores${queryDePeriodo(de, ate)}`));

export const listarConversas = (de?: string | null, ate?: string | null) =>
  proteger(buscar<ResumoConversa[]>(`/conversas${queryDePeriodo(de, ate)}`));

export type TermoDoLexico = {
  termo: string;
  ocorrencias: number;
  /** Quanto o termo e mais frequente nesta classe do que nas outras, em [-1, 1]. */
  distincao: number;
};

export type ClasseDoLexico = {
  categoria: Categoria;
  atendimentos: number;
  palavras: TermoDoLexico[];
  emojis: TermoDoLexico[];
};

export const obterLexico = (de?: string | null, ate?: string | null) =>
  proteger(
    buscar<{ classes: ClasseDoLexico[] }>(`/lexico${queryDePeriodo(de, ate)}`),
  );

export type Camada = "lexico" | "dominio" | "proveniencia";

export type TipoDeNo =
  | "conversa"
  | "categoria"
  | "canal"
  | "desfecho"
  | "termo"
  | "emoji"
  | "feature"
  | "fonte"
  | "importacao";

export type NoDoGrafo = {
  id: string;
  tipo: TipoDeNo;
  camada: Camada;
  rotulo: string;
  grau: number;
  /**
   * Só existem em nós `conversa`, e `null` quer dizer SEM SINAL -- nunca zero.
   * Quem consumir isto com `?? 0` transforma "não se sabe" em "péssimo".
   */
  score?: number | null;
  nota?: number | null;
  categoria?: Categoria | null;
  sem_sinal?: boolean;
};

export type ArestaDoGrafo = {
  de: string;
  para: string;
  tipo: string;
  peso: number;
};

export type MetaDoGrafo = {
  camadas: Camada[];
  conversas: number;
  sem_sinal: number;
  termos_totais: number;
  termos_exibidos: number;
  truncado: boolean;
};

export type Grafo = {
  nos: NoDoGrafo[];
  arestas: ArestaDoGrafo[];
  meta: MetaDoGrafo;
};

/**
 * O grafo inteiro do periodo -- as tres camadas, sempre.
 *
 * A rota `/grafo` aceita um parametro `camadas` que recorta quais delas
 * voltam, e este cliente NAO o envia de proposito. O foco de camada da tela
 * do grafo e CLIENTE: ele muda a opacidade do que ja esta desenhado, sem
 * refetch. Buscar de novo devolveria outro conjunto de nos, o que reiniciaria
 * a simulacao e rearranjaria o layout inteiro a cada troca de camada -- e
 * apagaria do dado justamente as arestas ENTRE camadas, que sao o motivo de
 * aquilo ser um grafo so em vez de tres abas.
 *
 * Quem um dia precisar do recorte no SERVIDOR (um export, uma tela que so
 * olhe lexico) acrescenta o parametro aqui em uma linha. Ate la ele nao
 * existe, para ninguem confundi-lo com o caminho da regua de foco.
 */
export const obterGrafo = (de?: string | null, ate?: string | null) =>
  proteger(buscar<Grafo>(`/grafo${queryDePeriodo(de, ate)}`));

export const obterConversa = (id: string) =>
  proteger(buscar<DetalheConversa>(`/conversas/${encodeURIComponent(id)}`));

export const obterAtribuicao = (id: string) =>
  proteger(
    buscar<Atribuicao>(`/conversas/${encodeURIComponent(id)}/atribuicao`),
  );

export const obterModelo = () => proteger(buscar<FichaModelo>("/modelo"));

/** Uma pagina do lexicon de emoji. `busca` casa o emoji exato, como a API faz. */
export const obterLexicon = (
  { busca, limite, deslocamento }: {
    busca?: string;
    limite: number;
    deslocamento: number;
  },
) => {
  const parametros = new URLSearchParams({
    limite: String(limite),
    deslocamento: String(deslocamento),
  });
  if (busca) parametros.set("busca", busca);
  return proteger(buscar<PaginaLexicon>(`/modelo/lexicon?${parametros}`));
};

/**
 * Roda o classificador numa frase avulsa. Nao persiste nada.
 *
 * Ao contrario das leituras, esta e uma chamada do NAVEGADOR (o simulador e
 * interativo): `urlDaApi` a manda para o proxy, que anexa a chave no servidor.
 */
export async function simularTexto(texto: string): Promise<Resultado<Simulacao>> {
  return proteger(
    (async () => {
      const resposta = await fetch(urlDaApi("/modelo/simular"), {
        method: "POST",
        headers: await cabecalhosDaApi({ "Content-Type": "application/json" }),
        body: JSON.stringify({ texto }),
        cache: "no-store",
      });
      if (!resposta.ok) {
        // A API responde 400 com `{detail}` -- mostrar o motivo real vale mais
        // que "erro 400" para quem esta demonstrando o produto.
        const corpo = (await resposta.json().catch(() => null)) as
          | { detail?: string }
          | null;
        throw new Error(
          corpo?.detail ?? `/modelo/simular respondeu ${resposta.status}`,
        );
      }
      return (await resposta.json()) as Simulacao;
    })(),
  );
}

export async function simularIroniaLaya(
  texto: string,
): Promise<Resultado<SimulacaoIroniaLaya>> {
  return proteger(
    (async () => {
      const resposta = await fetch(urlDaApi("/modelo/ironia-laya/simular"), {
        method: "POST",
        headers: await cabecalhosDaApi({ "Content-Type": "application/json" }),
        body: JSON.stringify({ texto }),
        cache: "no-store",
      });
      if (!resposta.ok) {
        const corpo = (await resposta.json().catch(() => null)) as
          | { detail?: string }
          | null;
        throw new Error(
          corpo?.detail ?? `/modelo/ironia-laya/simular respondeu ${resposta.status}`,
        );
      }
      return (await resposta.json()) as SimulacaoIroniaLaya;
    })(),
  );
}

/**
 * Configuracao vigente + de fabrica.
 *
 * Chamada tambem pelas telas de leitura: os limiares de latencia que qualificam
 * "rapido/aceitavel/lento" saem daqui, nao de constante no front.
 */
export const obterConfiguracoes = () =>
  proteger(buscar<Configuracoes>("/configuracoes"));

export type EstadoDeAcesso = {
  ligada: boolean;
  /** De onde vem a mestra vigente. O ambiente vence o banco. */
  origem: "ambiente" | "banco" | null;
};

/**
 * A autenticacao da API esta ligada, e por qual procedencia.
 *
 * Unica leitura que funciona SEM credencial -- a rota e isenta do middleware de
 * chave de proposito, porque a tela precisa dela justamente quando ainda nao ha
 * chave nenhuma para apresentar.
 */
export const obterEstadoDeAcesso = () =>
  proteger(buscar<EstadoDeAcesso>("/acesso/estado"));

/**
 * Grava as chaves enviadas. Manda so o que mudou -- o `PUT` valida chave a
 * chave, entao enviar o bloco inteiro faria um erro de latencia recusar
 * tambem uma faixa de NPS correta.
 */
export const salvarConfiguracoes = (valores: Partial<ValoresConfiguracao>) =>
  proteger(escrever<Configuracoes>("/configuracoes", "PUT", valores));

export const listarFontes = () =>
  proteger(buscar<FonteIntegracao[]>("/integracoes/fontes"));

export const criarFonte = (fonte: {
  nome: string;
  canal: string;
  tipo: string;
  /** NOME da variavel de ambiente. A credencial nunca passa por aqui. */
  variavel_segredo?: string | null;
}) => proteger(escrever<FonteIntegracao>("/integracoes/fontes", "POST", fonte));

export const ajustarFonte = (
  id: number,
  /** `variavel_segredo: null` limpa; ausente não mexe. É o NOME, nunca o segredo. */
  mudanca: { nome?: string; ativa?: boolean; variavel_segredo?: string | null },
) =>
  proteger(
    escrever<FonteIntegracao>(`/integracoes/fontes/${id}`, "PATCH", mudanca),
  );

/** Remove o CADASTRO da fonte. Nenhum atendimento e apagado junto. */
export const apagarFonte = (id: number) =>
  proteger(escrever<void>(`/integracoes/fontes/${id}`, "DELETE"));

export type ChaveGerada = {
  fonte: FonteIntegracao;
  /**
   * A chave EM CLARO. Este e o unico lugar em toda a API onde ela existe, e
   * so nesta resposta: o servidor guarda apenas o hash e nao ha rota para
   * reler. A tela precisa mostra-la agora ou ela se perde.
   *
   * NUNCA guardar isto em localStorage, sessionStorage ou URL -- ela morre
   * junto com o estado do componente, de proposito.
   */
  chave: string;
  aviso: string;
};

/**
 * Gera a chave de API da fonte, SUBSTITUINDO a anterior.
 *
 * Duas chaves validas ao mesmo tempo pareceriam rotacao sem risco, mas a
 * antiga seguiria aceita sem ninguem saber quem ainda a usa.
 */
export const gerarChave = (id: number) =>
  proteger(escrever<ChaveGerada>(`/integracoes/fontes/${id}/chave`, "POST"));

/** Invalida a chave. A fonte e os atendimentos dela continuam. */
export const revogarChave = (id: number) =>
  proteger(escrever<void>(`/integracoes/fontes/${id}/chave`, "DELETE"));

export type TipoDeFonte = { valor: string; rotulo: string; ajuda: string };

/**
 * Os tipos que a ingestao sabe tratar.
 *
 * Lidos da API de proposito: a tela mantinha a propria copia da lista, e copia
 * so fica errada no dia em que um tipo novo entra no servidor -- o formulario
 * seguiria oferecendo os antigos, sem erro nenhum, so sumindo da vista.
 */
export const listarTiposDeFonte = () =>
  proteger(buscar<TipoDeFonte[]>("/integracoes/tipos"));

/**
 * O veredito de uma entrega de webhook. A lista vem de `VEREDITOS` em
 * `fraus/db.py` e e digitada aqui uma unica vez -- se um veredito novo entrar
 * la sem entrar aqui, o TypeScript reclama no `switch` de `Entregas.tsx`, que
 * e exatamente onde a divergencia precisa aparecer.
 */
export type Veredito =
  | "aceita"
  | "assinatura"
  | "fora_da_janela"
  | "duplicada"
  | "corpo_invalido"
  | "fonte_inativa"
  | "sem_segredo"
  | "tipo_incompativel";

/** Uma linha do historico de `GET /integracoes/fontes/{id}/entregas`. */
export type Entrega = {
  id: number;
  fonte_id: number;
  webhook_id: string | null;
  recebida_em: string;
  veredito: Veredito;
  motivo: string | null;
  /** `null` quando a entrega nao gerou conversa -- nunca "" nem 0. */
  conversa_id: string | null;
};

/** Historico de entregas de webhook da fonte, mais recente primeiro. */
export const listarEntregas = (fonteId: number) =>
  proteger(buscar<Entrega[]>(`/integracoes/fontes/${fonteId}/entregas`));

/** Resposta de `POST /integracoes/fontes/{id}/segredo`. */
export type SegredoGerado = {
  segredo: string;
  /** `null` quando a fonte nao nomeia variavel de ambiente nenhuma. */
  variavel: string | null;
  aviso: string;
};

/**
 * Gera o segredo de assinatura do webhook da fonte, devolvido EM CLARO uma
 * unica vez -- o servidor nao grava a credencial que emite, nem o hash.
 */
export const gerarSegredo = (fonteId: number) =>
  proteger(escrever<SegredoGerado>(`/integracoes/fontes/${fonteId}/segredo`, "POST"));

export type ArquivoImportavel = { caminho: string; bytes: number };

/** Os CSV disponiveis na raiz de importacao, com caminho relativo a ela. */
export const listarArquivosImportaveis = () =>
  proteger(
    buscar<{ raiz: string; arquivos: ArquivoImportavel[] }>(
      "/integracoes/arquivos",
    ),
  );

export type ResultadoImportacao = {
  importadas: number;
  rejeitadas: number;
  motivos: { numero_linha: number; motivo: string }[];
};

/**
 * Importa um CSV da raiz. O `caminho` e o que a listagem devolveu, sem ajuste.
 *
 * O servidor recusa qualquer caminho que escape da raiz; a interface nunca
 * monta caminho a mao nem oferece campo livre para isso.
 */
/**
 * Como o arquivo da pasta SERIA importado, sem gravar. `exige_confirmacao`
 * diz que a importação vai recusar (409) até as colunas virarem perfil.
 * O ajuste de colunas vale só aqui: a importação lê o perfil salvo, nunca
 * um mapeamento enviado no corpo.
 */
export const previaImportacao = (caminho: string, opcoes: OpcoesDeLeitura = {}) =>
  proteger(
    escrever<PreviaLeitura & { exige_confirmacao: boolean }>(
      "/conversas/importar/previa",
      "POST",
      {
        caminho,
        mapeamento: opcoes.mapeamento ?? null,
        ordem_data: opcoes.ordemData ?? null,
      },
    ),
  );

export const importarArquivo = (caminho: string) =>
  proteger(
    escrever<ResultadoImportacao>("/conversas/importar", "POST", { caminho }),
  );

export const listarImportacoes = () =>
  proteger(buscar<Importacao[]>("/integracoes/importacoes"));

/**
 * Peso de UMA palavra na leitura que o modelo fez da mensagem.
 *
 * Medido por oclusao: apaga-se a palavra e pergunta-se de novo. Positivo
 * empurrou para satisfeito, negativo para insatisfeito.
 *
 * `peso: null` NAO e o mesmo que `0`. Zero e medicao ("apagar esta palavra nao
 * mudou nada"); nulo e ausencia de medicao -- a mensagem passou do teto de
 * palavras que o servidor mede. A tela precisa distinguir os dois.
 *
 * `inicio`/`fim` sao indices no texto original, para grifar sem re-tokenizar:
 * uma segunda tokenizacao no cliente acabaria grifando trecho diferente do que
 * o servidor mediu.
 */
export type PesoDePalavra = {
  palavra: string;
  inicio: number;
  fim: number;
  peso: number | null;
};

/** Palavra mais usada pelo cliente, comparada ao restante do banco. */
export type ItemVocabulario = {
  palavra: string;
  vezes: number;
  /**
   * Quantas vezes a palavra e mais frequente aqui do que na referencia --
   * `3.0` e "o triplo do normal nesta operacao". `null` quando a palavra nao
   * aparece na referencia: nao ha com o que comparar, e `1.0` afirmaria
   * "igual a media" sem ter medido media nenhuma.
   */
  destaque: number | null;
};

export type MensagemAnalisada = MensagemAtribuida & {
  /** `null` para bot e humano: so a fala do cliente recebe peso de palavra. */
  palavras: PesoDePalavra[] | null;
};

/** Os dois motivos para nao haver nota. Ver `fraus/modelos.py`. */
export type MotivoSemSinal = "sem_fala_do_cliente" | "so_cortesia";

export type ConversaAnalisada = {
  conversa: DetalheConversa;
  score: number | null;
  /** Ver `motivo_sem_sinal` em `ResumoConversa`. */
  motivo_sem_sinal: MotivoSemSinal | null;
  nota: number | null;
  categoria: Categoria | null;
  mensagens: MensagemAnalisada[];
  contribuicoes: Record<string, number> | null;
  importancias: Record<string, number>;
  sinais_fora_do_score: string[];
  vocabulario: ItemVocabulario[];
  qtd_mensagens: number;
  qtd_cliente: number;
  qtd_bot: number;
  qtd_humano: number;
  latencia_primeira_resposta_s: number | null;
  latencia_mediana_s: number | null;
  latencia_mediana_bot_s: number | null;
  latencia_mediana_humano_s: number | null;
  duracao_s: number;
  desfecho: Desfecho;
};

export type ResultadoAnalise = {
  analises: ConversaAnalisada[];
  conversas_no_arquivo: number;
  conversas_analisadas: number;
  rejeitadas: { numero_linha: number; motivo: string }[];
  total_rejeitadas: number;
  /** Quantas conversas do banco serviram de referencia para o `destaque`. */
  referencia_conversas: number;
  /** Como o arquivo foi entendido: "export da Totalk", "transcrição em pdf"… */
  formato: string;
  /**
   * Falso quando o arquivo nao traz horario (tipico de .docx e .pdf).
   *
   * Sem horario nao ha latencia, e latencia e feature do
   * fusor -- entao a conversa NAO recebe nota. Nao e falha: e a resposta
   * honesta. Zerar o tempo faria o modelo ler como se toda resposta tivesse
   * sido instantanea e a nota sairia melhor que a verdade.
   */
  tem_tempo: boolean;
  /** O que a leitura teve que inferir. Exibir sempre, não só quando dá errado. */
  avisos: string[];
  /** Presente só quando as colunas foram INFERIDAS pelo mapeador. */
  mapeamento: MapeamentoInferido | null;
  perfil: { id: number; nome: string } | null;
};

/** Os papéis que o mapeador procura. `texto` e `autor` são obrigatórios. */
export const PAPEIS = ["texto", "autor", "enviada_em", "conversa_id", "canal"] as const;
export type Papel = (typeof PAPEIS)[number];
export type OrdemData = "dia/mes" | "mes/dia";

export type PapelAtribuido = {
  coluna: string;
  /** 0–1. "confirmado" no motivo quando veio do analista ou de perfil. */
  confianca: number;
  motivo: string;
};

export type MapeamentoInferido = {
  colunas: string[];
  assinatura: string;
  papeis: Partial<Record<Papel, PapelAtribuido>>;
  ordem_data: OrdemData | null;
  /** Nenhum campo passou de 12: a ordem foi desempatada ou suposta. */
  data_ambigua: boolean;
};

/** O que o analista confirma: papel -> coluna, `null` = "o arquivo não tem". */
export type MapeamentoConfirmado = Partial<Record<Papel, string | null>>;

export type OpcoesDeLeitura = {
  mapeamento?: MapeamentoConfirmado;
  ordemData?: OrdemData | null;
};

export type PreviaLeitura = {
  formato: string;
  tem_tempo: boolean;
  conversas: number;
  mensagens: number;
  avisos: string[];
  total_rejeitadas: number;
  rejeitadas: { numero_linha: number; motivo: string }[];
  mapeamento: MapeamentoInferido | null;
  /** Primeiras linhas, já censuradas pelo servidor. */
  amostra: string[][];
  perfil: { id: number; nome: string } | null;
};

export type PerfilMapeamento = {
  id: number;
  nome: string;
  assinatura: string;
  colunas: string[];
  papeis: MapeamentoConfirmado;
  ordem_data: OrdemData | null;
  criado_em: string;
};

/**
 * Analisa um arquivo de conversa SEM gravar nada.
 *
 * O conteudo vai no corpo e e interpretado em memoria: nada entra no banco,
 * nada toca o disco. E o que separa esta chamada da importacao -- aqui se
 * pergunta "o que o modelo acha disto?", nao "passe a contar isto no NPS".
 */
export const analisarArquivo = (csv: string) =>
  proteger(escrever<ResultadoAnalise>("/analisar", "POST", { csv }));

/**
 * Analisa um arquivo -- csv, xlsx, json, txt (WhatsApp ou prosa), docx ou pdf.
 *
 * Vai como multipart e nao como JSON porque planilha e PDF nao sao texto:
 * codificar em base64 para caber num campo de string inflaria o corpo em um
 * terco sem ganhar nada. Continua sem gravar coisa alguma no servidor.
 */
export async function analisarUpload(
  arquivo: File,
  opcoes: OpcoesDeLeitura = {},
): Promise<Resultado<ResultadoAnalise>> {
  return proteger(enviarArquivo<ResultadoAnalise>("/analisar/arquivo", arquivo, opcoes, ESPERA_ANALISE_MS));
}

/**
 * Como o arquivo SERIA lido, sem modelo e sem gravar nada -- a etapa de
 * conferência de colunas. Rápida: pode ser chamada a cada ajuste na tela.
 */
export async function previaUpload(
  arquivo: File,
  opcoes: OpcoesDeLeitura = {},
): Promise<Resultado<PreviaLeitura>> {
  return proteger(enviarArquivo<PreviaLeitura>("/analisar/previa", arquivo, opcoes, ESPERA_ESCRITA_MS));
}

export const listarPerfisMapeamento = () =>
  proteger(buscar<PerfilMapeamento[]>("/perfis-mapeamento"));

export const salvarPerfilMapeamento = (perfil: {
  nome: string;
  colunas: string[];
  papeis: MapeamentoConfirmado;
  ordem_data: OrdemData | null;
}) => proteger(escrever<PerfilMapeamento>("/perfis-mapeamento", "POST", perfil));

export const apagarPerfilMapeamento = (id: number) =>
  proteger(escrever<void>(`/perfis-mapeamento/${id}`, "DELETE"));

async function enviarArquivo<T>(
  rota: string,
  arquivo: File,
  opcoes: OpcoesDeLeitura,
  espera: number,
): Promise<T> {
  const corpo = new FormData();
  corpo.append("arquivo", arquivo);
  // O mapeamento diz só qual coluna faz qual papel -- nunca nota
  // (invariante 3): o veredito continua saindo do servidor.
  if (opcoes.mapeamento) corpo.append("mapeamento", JSON.stringify(opcoes.mapeamento));
  if (opcoes.ordemData) corpo.append("ordem_data", opcoes.ordemData);
  // Sem Content-Type a mao: o `fetch` precisa gerar o boundary do
  // multipart, e fixa-lo aqui quebraria o parse do lado da API.
  const resposta = await fetch(urlDaApi(rota), {
    method: "POST",
    headers: await cabecalhosDaApi(),
    body: corpo,
    // Teto largo: a inferencia roda em CPU e mediu 21,8 s no arquivo maior
    // que o teto de mensagens deixa passar. Mas nao INFINITO -- foi
    // exatamente aqui que a tela ficou 60 s presa esperando uma API que
    // havia travado, e o 502 do proxy chegou antes de qualquer aviso nosso.
    signal: AbortSignal.timeout(espera),
  });
  if (falhouNoProxy(resposta.status)) {
    throw new Error(`${MARCA_API_FORA} ${urlDaApi("")}`);
  }
  if (!resposta.ok) {
    // O `detail` do FastAPI e a mensagem que NOMEIA o que se esperava --
    // ela e o produto principal de uma recusa, e perde-la deixaria o
    // operador com "erro 400" e nada para consertar.
    const erro = await resposta.json().catch(() => null);
    throw new Error(erro?.detail ?? `A API respondeu ${resposta.status}.`);
  }
  return (await resposta.json()) as T;
}

export type PontoSerieApi = {
  dia: string; // AAAA-MM-DD
  nps: number | null;
  latencia_mediana_s: number | null;
  atendimentos: number;
  com_score: number;
};

/**
 * Serie diaria de NPS x latencia, ja agregada pelo servidor.
 *
 * O recorte vai como `?de=&ate=` e as duas pontas sao INCLUSIVAS. Data
 * malformada devolve 400 em vez de ser ignorada -- filtro descartado em
 * silencio faria o grafico mostrar a serie inteira parecendo o recorte.
 */
export const obterSerieTemporal = (de?: string | null, ate?: string | null) => {
  const query = new URLSearchParams();
  if (de) query.set("de", de);
  if (ate) query.set("ate", ate);
  const sufixo = query.toString();
  return proteger(
    buscar<{ de: string | null; ate: string | null; pontos: PontoSerieApi[] }>(
      `/serie-temporal${sufixo ? `?${sufixo}` : ""}`,
    ),
  );
};

/** Estado de saude da API -- alimenta o indicador do app shell. */
/**
 * `motor` diz QUAL motor respondeu, e o campo existe por um defeito real de
 * 04/09/2026: com o `scripts/api_demo.py` no dublê, esta tela escreveu "API no
 * ar" durante um dia inteiro enquanto todo número exibido era sintético.
 * "Respondeu" e "está medindo" são afirmações diferentes.
 *
 * Opcional no tipo de propósito: uma API mais antiga não manda o campo, e
 * `undefined` ali significa "não deu para saber" — que o servidor da interface
 * trata como possivelmente dublê, nunca como real confirmado.
 */
export const obterSaude = () =>
  proteger(
    buscar<{
      status: string;
      motor?: "real" | "duble";
      estado_motor?: "frio" | "carregando" | "pronto" | "erro";
    }>("/saude"),
  );

const LOTE_DETALHES = 8;

/**
 * Teto de transcricoes que o PLANO B busca de uma vez.
 *
 * `obterDetalhes` so roda quando um agregado do servidor FALHOU -- e o
 * periodo pedido pode ser "todos", sem limite de tamanho. Sem este teto, uma
 * instalacao com milhares de atendimentos vira dezenas de lotes SEQUENCIAIS
 * de `LOTE_DETALHES`, presos dentro do render da pagina: uma API ja
 * DEGRADADA (nao caida, so lenta -- e foi exatamente a falha de um agregado
 * que disparou o plano B) fica mais lenta ainda recebendo essa tempestade, e
 * quem espera a tela ve isso como travamento, nao como "alguns dados nao
 * carregaram".
 *
 * 200 cobre o recorte tipico de um mes sem gerar uma cadeia de mais de 25
 * lotes. NENHUM CORTE E SILENCIOSO: `truncadas` volta para quem chama, para a
 * tela poder dizer o que ficou de fora em vez de fingir que o recorte inteiro
 * foi considerado.
 */
export const TETO_DETALHES_PLANO_B = 200;

/**
 * Busca as transcricoes de varias conversas.
 *
 * A serie temporal SAIU daqui: ela vem agregada de `GET /serie-temporal`. O
 * N+1 sobrevive para o que ainda nao tem agregado no servidor -- o lexico por
 * classe e o tempo mediano de resposta da faixa de indicadores, que continuam
 * precisando do texto e dos timestamps de cada transcricao. Eliminar o resto
 * exige `GET /indicadores?de=&ate=` e um agregado de lexico.
 *
 * Conversas que falharem individualmente sao descartadas em vez de derrubar a
 * pagina inteira.
 */
export async function obterDetalhes(
  ids: string[],
): Promise<{ detalhes: DetalheConversa[]; falhas: number; truncadas: number }> {
  const considerados = ids.slice(0, TETO_DETALHES_PLANO_B);
  const truncadas = ids.length - considerados.length;
  const detalhes: DetalheConversa[] = [];
  let falhas = 0;

  for (let inicio = 0; inicio < considerados.length; inicio += LOTE_DETALHES) {
    const lote = considerados.slice(inicio, inicio + LOTE_DETALHES);
    const resultados = await Promise.all(lote.map((id) => obterConversa(id)));
    for (const resultado of resultados) {
      if (resultado.ok) detalhes.push(resultado.dado);
      else falhas += 1;
    }
  }

  return { detalhes, falhas, truncadas };
}

/**
 * O endereco que a interface EXIBE como destino das chamadas do navegador
 * (tooltip do indicador de saude). E o proxy, porque e para la que o navegador
 * fala -- mostrar a URL interna da API confundiria e ainda a divulgaria.
 */
export const ENDERECO_API = PROXY;
