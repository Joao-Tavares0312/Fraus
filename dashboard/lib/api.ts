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

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Categoria = "detrator" | "neutro" | "promotor";

export type Indicadores = {
  /** null quando nenhum atendimento tem score: ausencia de dado nao e zero. */
  nps: number | null;
  /** null quando nenhum atendimento tem score. */
  csat: number | null;
  /** Contencao NAO depende de score, entao sempre e um numero. */
  containment_rate: number;
  total_conversas: number;
  sem_sinal: number;
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
};

export type Autor = "cliente" | "bot" | "humano";

export type Mensagem = {
  autor: Autor;
  texto: string;
  enviada_em: string;
};

export type DetalheConversa = ResumoConversa & {
  encerrada_em: string | null;
  escalou_para_humano: boolean;
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
};

/** Resposta de `GET /conversas/{id}/atribuicao`. */
export type Atribuicao = {
  conversa_id: string;
  /** Os mesmos score/nota/categoria de `/conversas/{id}`: gravados na importacao. */
  score: number | null;
  nota: number | null;
  categoria: Categoria | null;
  mensagens: MensagemAtribuida[];
  /** Peso absoluto GLOBAL de cada uma das 16 features do fusor -- aprendido
   * no treino, nao especifico desta conversa. */
  importancias: Record<string, number>;
  /** Quanto cada feature pesou NESTA conversa: positivo empurrou para
   * satisfeito, negativo para insatisfeito. `null` quando nao ha fala do
   * cliente -- sem score, sem contribuicao. */
  contribuicoes: Record<string, number> | null;
};

/** Metricas do treino, exportadas pelo notebook 01. `null` ate o treino rodar. */
export type MetricasTreino = {
  acuracia?: number;
  f1_macro?: number;
  [chave: string]: unknown;
};

/** Resposta de `GET /modelo` -- a ficha do modelo. */
export type FichaModelo = {
  /** Peso GLOBAL de cada uma das 16 features. Nao e especifico de conversa. */
  importancias: Record<string, number>;
  /** `null` enquanto o notebook 01 nao exportou metricas.json. NUNCA zero. */
  metricas: MetricasTreino | null;
  classes: string[];
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

async function buscar<T>(rota: string): Promise<T> {
  const resposta = await fetch(`${BASE}${rota}`, { cache: "no-store" });
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
  const resposta = await fetch(`${BASE}${rota}`, {
    method: metodo,
    headers: corpo === undefined ? undefined : { "Content-Type": "application/json" },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
    cache: "no-store",
  });

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

function mensagemDeErro(erro: unknown): string {
  if (erro instanceof Error) {
    // `fetch` recusado dá "fetch failed" — inútil para quem está na banca.
    if (/fetch failed|ECONNREFUSED/i.test(erro.message)) {
      return `API não respondeu em ${BASE}`;
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

export const obterIndicadores = () =>
  proteger(buscar<Indicadores>("/indicadores"));

export const listarConversas = () =>
  proteger(buscar<ResumoConversa[]>("/conversas"));

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
 * interativo), entao `BASE` precisa ser alcancavel do cliente -- por isso a
 * variavel de ambiente e `NEXT_PUBLIC_API_URL`.
 */
export async function simularTexto(texto: string): Promise<Resultado<Simulacao>> {
  return proteger(
    (async () => {
      const resposta = await fetch(`${BASE}/modelo/simular`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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

/**
 * Configuracao vigente + de fabrica.
 *
 * Chamada tambem pelas telas de leitura: os limiares de latencia que qualificam
 * "rapido/aceitavel/lento" saem daqui, nao de constante no front.
 */
export const obterConfiguracoes = () =>
  proteger(buscar<Configuracoes>("/configuracoes"));

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
  mudanca: { nome?: string; ativa?: boolean },
) =>
  proteger(
    escrever<FonteIntegracao>(`/integracoes/fontes/${id}`, "PATCH", mudanca),
  );

/** Remove o CADASTRO da fonte. Nenhum atendimento e apagado junto. */
export const apagarFonte = (id: number) =>
  proteger(escrever<void>(`/integracoes/fontes/${id}`, "DELETE"));

export const listarImportacoes = () =>
  proteger(buscar<Importacao[]>("/integracoes/importacoes"));

/** Estado de saude da API -- alimenta o indicador do app shell. */
export const obterSaude = () =>
  proteger(buscar<{ status: string }>("/saude"));

const LOTE_DETALHES = 8;

/**
 * Busca as transcricoes de varias conversas.
 *
 * A API nao expoe serie temporal nem latencia agregada, entao a pagina
 * principal deriva as duas dos timestamps das mensagens -- o que obriga a
 * baixar as transcricoes. E um N+1 assumido, aceitavel no volume do trabalho
 * (dezenas de atendimentos) e resolvido por um `GET /serie-temporal` no
 * servidor. Conversas que falharem individualmente sao descartadas em vez de
 * derrubar a pagina inteira.
 */
export async function obterDetalhes(
  ids: string[],
): Promise<{ detalhes: DetalheConversa[]; falhas: number }> {
  const detalhes: DetalheConversa[] = [];
  let falhas = 0;

  for (let inicio = 0; inicio < ids.length; inicio += LOTE_DETALHES) {
    const lote = ids.slice(inicio, inicio + LOTE_DETALHES);
    const resultados = await Promise.all(lote.map((id) => obterConversa(id)));
    for (const resultado of resultados) {
      if (resultado.ok) detalhes.push(resultado.dado);
      else falhas += 1;
    }
  }

  return { detalhes, falhas };
}

export { BASE as ENDERECO_API };
