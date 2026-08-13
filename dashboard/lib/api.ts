/**
 * Cliente da API do Dolos.
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
  /** Peso absoluto de cada uma das 16 features do fusor. */
  importancias: Record<string, number>;
};

export type Resultado<T> =
  | { ok: true; dado: T }
  | { ok: false; erro: string };

async function buscar<T>(rota: string): Promise<T> {
  const resposta = await fetch(`${BASE}${rota}`, { cache: "no-store" });
  if (!resposta.ok) throw new Error(`${rota} respondeu ${resposta.status}`);
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
