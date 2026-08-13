/**
 * Derivacoes feitas no cliente da API a partir do que os endpoints DAO.
 *
 * A API do Dolos expoe indicadores agregados, a lista de conversas, a
 * transcricao e a atribuicao por sentenca. Ela NAO expoe serie temporal,
 * latencia agregada nem lexico por classe. Tudo que este arquivo calcula sai
 * dos timestamps e do texto que a transcricao ja entrega -- nada aqui inventa
 * numero. O que nao da para derivar honestamente nao esta aqui: esta como
 * estado vazio na interface, nomeando o endpoint que resolveria.
 *
 * A atribuicao por sentenca NAO e derivada aqui: ela vem pronta de
 * `GET /conversas/{id}/atribuicao`. As funcoes desta secao so dao FORMA ao
 * que o servidor mandou (classe dominante, saldo, agregacao por sinal).
 *
 * A regra de latencia e a MESMA de `dolos/sinais/tempo.py`: o intervalo de
 * cada mensagem do cliente ate a proxima resposta (bot ou humano).
 */

import lexicoEmoji from "./lexicoEmoji.json";
import type {
  Categoria,
  DetalheConversa,
  Mensagem,
  MensagemAtribuida,
  ResumoConversa,
} from "./api";

const RESPONDENTES = new Set(["bot", "humano"]);
const POLARIDADE: Record<string, number> = lexicoEmoji;

// ---------------------------------------------------------------------------
// Faixas de NPS (0-6 detrator, 7-8 neutro, 9-10 promotor)
// ---------------------------------------------------------------------------

export const FAIXAS_NPS = [
  { categoria: "detrator" as Categoria, de: 0, ate: 6, rotulo: "0–6 detrator" },
  { categoria: "neutro" as Categoria, de: 7, ate: 8, rotulo: "7–8 neutro" },
  { categoria: "promotor" as Categoria, de: 9, ate: 10, rotulo: "9–10 promotor" },
];

/** Faixa saudavel de referencia do CSAT, em pontos percentuais. */
export const CSAT_SAUDAVEL = { de: 75, ate: 85 };

/*
 * NAO existe aqui uma funcao `notaDeScore`. A nota 0-10 e derivada NO SERVIDOR
 * (`dolos/indicadores.py::nota_0_10`) e vem pronta em `/conversas` e em
 * `/conversas/{id}`. Recalcular no cliente ja custou uma divergencia real:
 * `round` do Python e bancario (`round(6.5) == 6`) e `Math.round` arredonda
 * meio para cima (`Math.round(6.5) == 7`), entao score 65 exibia nota 7 na
 * mesma linha em que a categoria dizia "Detrator". Uma fonte so.
 */

export function categoriaDaNota(nota: number): Categoria {
  if (nota <= 6) return "detrator";
  if (nota <= 8) return "neutro";
  return "promotor";
}

export function npsDeCategorias(categorias: Categoria[]): number | null {
  if (categorias.length === 0) return null;
  const promotores = categorias.filter((c) => c === "promotor").length;
  const detratores = categorias.filter((c) => c === "detrator").length;
  return (100 * (promotores - detratores)) / categorias.length;
}

// ---------------------------------------------------------------------------
// Estatistica minima
// ---------------------------------------------------------------------------

export function mediana(valores: number[]): number | null {
  if (valores.length === 0) return null;
  const ordenados = [...valores].sort((a, b) => a - b);
  const meio = Math.floor(ordenados.length / 2);
  return ordenados.length % 2 === 1
    ? ordenados[meio]
    : (ordenados[meio - 1] + ordenados[meio]) / 2;
}

// ---------------------------------------------------------------------------
// Latencia por mensagem
// ---------------------------------------------------------------------------

export type LatenciaAnotada = {
  /** Indice da mensagem RESPONDENTE dentro de `mensagens`. */
  indice: number;
  segundos: number;
};

export function latenciasAnotadas(mensagens: Mensagem[]): LatenciaAnotada[] {
  const anotadas: LatenciaAnotada[] = [];
  for (let i = 0; i < mensagens.length; i += 1) {
    if (mensagens[i].autor !== "cliente") continue;
    for (let j = i + 1; j < mensagens.length; j += 1) {
      if (!RESPONDENTES.has(mensagens[j].autor)) continue;
      const segundos =
        (new Date(mensagens[j].enviada_em).getTime() -
          new Date(mensagens[i].enviada_em).getTime()) /
        1000;
      anotadas.push({ indice: j, segundos });
      break;
    }
  }
  return anotadas;
}

export function latenciaMediana(mensagens: Mensagem[]): number | null {
  return mediana(latenciasAnotadas(mensagens).map((l) => l.segundos));
}

/**
 * Limiares de latencia, em segundos, calibrados pela literatura de live chat
 * que a propria tela cita. Sao a UNICA fonte dos numeros que aparecem nos
 * rotulos -- texto e limiar nao podem divergir.
 */
export const LIMIARES_LATENCIA = {
  /** Ate aqui a satisfacao esta no pico observado (~84,7% de CSAT). */
  pico: 10,
  /** Ate aqui a espera ainda e saudavel. */
  saudavel: 60,
  /** Ate aqui a satisfacao degrada: -2 a -3 pontos de CSAT por minuto extra. */
  degradando: 180,
} as const;

/**
 * Faixa de severidade da espera.
 *
 * "critica" comeca em 3 MINUTOS, nao em 1: a fonte de live chat atribui o
 * abandono (57% dos clientes) a espera acima de tres minutos, e a perda por
 * minuto extra e de 2 a 3 pontos de CSAT. Atribuir 1 minuto ao abandono seria
 * erro factual numa tela que cita a fonte.
 */
export type SeveridadeLatencia = "pico" | "saudavel" | "degradando" | "abandono";

export function severidadeLatencia(segundos: number): SeveridadeLatencia {
  if (segundos <= LIMIARES_LATENCIA.pico) return "pico";
  if (segundos <= LIMIARES_LATENCIA.saudavel) return "saudavel";
  if (segundos <= LIMIARES_LATENCIA.degradando) return "degradando";
  return "abandono";
}

/** Rotulo e justificativa de cada faixa. Um texto so, citado igual em toda a tela. */
export const ROTULO_LATENCIA: Record<
  SeveridadeLatencia,
  { titulo: string; detalhe: string }
> = {
  pico: {
    titulo: "Resposta imediata",
    detalhe: `até ${LIMIARES_LATENCIA.pico} s — pico de satisfação na literatura de live chat (CSAT ~84,7%)`,
  },
  saudavel: {
    titulo: "Espera saudável",
    detalhe: `entre ${LIMIARES_LATENCIA.pico} s e ${LIMIARES_LATENCIA.saudavel} s — fora do pico, ainda dentro do saudável`,
  },
  degradando: {
    titulo: "Espera longa",
    detalhe: `entre ${LIMIARES_LATENCIA.saudavel} s e ${LIMIARES_LATENCIA.degradando / 60} min — a satisfação degrada de 2 a 3 pontos de CSAT por minuto extra`,
  },
  abandono: {
    titulo: "Espera crítica",
    detalhe: `acima de ${LIMIARES_LATENCIA.degradando / 60} min — faixa de abandono: 57% dos clientes desistem`,
  },
};

// ---------------------------------------------------------------------------
// Serie temporal diaria (NPS inferido x latencia mediana)
// ---------------------------------------------------------------------------

export type PontoSerie = {
  dia: string; // AAAA-MM-DD
  rotulo: string; // DD/MM
  nps: number | null;
  latenciaMediana: number | null;
  atendimentos: number;
  comScore: number;
};

function chaveDoDia(iso: string): string {
  const data = new Date(iso);
  const mes = `${data.getMonth() + 1}`.padStart(2, "0");
  const dia = `${data.getDate()}`.padStart(2, "0");
  return `${data.getFullYear()}-${mes}-${dia}`;
}

export function serieDiaria(detalhes: DetalheConversa[]): PontoSerie[] {
  const porDia = new Map<
    string,
    { categorias: Categoria[]; latencias: number[]; atendimentos: number }
  >();

  for (const conversa of detalhes) {
    const dia = chaveDoDia(conversa.iniciada_em);
    const balde =
      porDia.get(dia) ?? { categorias: [], latencias: [], atendimentos: 0 };
    balde.atendimentos += 1;
    if (conversa.categoria) balde.categorias.push(conversa.categoria);
    const latencia = latenciaMediana(conversa.mensagens);
    if (latencia !== null) balde.latencias.push(latencia);
    porDia.set(dia, balde);
  }

  return [...porDia.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([dia, balde]): PontoSerie => {
      const [, mes, numero] = dia.split("-");
      return {
        dia,
        rotulo: `${numero}/${mes}`,
        nps: npsDeCategorias(balde.categorias),
        latenciaMediana: mediana(balde.latencias),
        atendimentos: balde.atendimentos,
        comScore: balde.categorias.length,
      };
    });
}

// ---------------------------------------------------------------------------
// Distribuicao de notas
// ---------------------------------------------------------------------------

export type BarraDistribuicao = {
  nota: number;
  rotulo: string;
  categoria: Categoria;
  quantidade: number;
};

export function distribuicaoDeNotas(resumos: ResumoConversa[]): {
  barras: BarraDistribuicao[];
  semSinal: number;
} {
  const contagem = new Array(11).fill(0) as number[];
  let semSinal = 0;

  for (const resumo of resumos) {
    if (resumo.nota === null) {
      semSinal += 1;
      continue;
    }
    contagem[Math.min(10, Math.max(0, resumo.nota))] += 1;
  }

  return {
    barras: contagem.map((quantidade, nota) => ({
      nota,
      rotulo: String(nota),
      categoria: categoriaDaNota(nota),
      quantidade,
    })),
    semSinal,
  };
}

// ---------------------------------------------------------------------------
// Lexico por classe: palavras e emojis
// ---------------------------------------------------------------------------

const PARADAS = new Set([
  "que", "para", "com", "uma", "por", "mais", "isso", "mas", "voce", "voces",
  "nao", "sim", "dos", "das", "aos", "sem", "sou", "esta", "estou", "meu",
  "minha", "seu", "sua", "ele", "ela", "eles", "elas", "como", "quando",
  "onde", "aqui", "ali", "esse", "essa", "este", "esta", "aquele", "aquela",
  "tem", "ter", "foi", "sao", "era", "vai", "vou", "ja", "ate", "pra", "pro",
  "the", "and", "num", "numa", "nos", "nas", "lhe", "ser", "fica", "faz",
  "muito", "todo", "toda", "todos", "todas", "outro", "outra", "entao",
  "porque", "pois", "quero", "queria", "preciso", "sobre", "depois", "antes",
]);

function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function palavras(texto: string): string[] {
  return normalizar(texto)
    .split(/[^a-z0-9]+/)
    .filter((palavra) => palavra.length >= 3 && !PARADAS.has(palavra));
}

const REGEX_EMOJI = /\p{Extended_Pictographic}/u;
const SEGMENTADOR = new Intl.Segmenter("pt-BR", { granularity: "grapheme" });

/**
 * Extrai emojis do texto recortando por CLUSTER DE GRAFEMA, nao por codepoint.
 *
 * E o mesmo recorte de `emoji.emoji_list` em `dolos/sinais/emoji.py`: 👍🏽
 * (com modificador de tom de pele) e 👨‍👩‍👧 (sequencia ZWJ) contam como UM
 * emoji, e nao como os 2-3 codepoints pictograficos que os compoem. Sem isso
 * a contagem de "top emojis" e a evidencia marcada divergiam do motor.
 */
export function emojisDoTexto(texto: string): string[] {
  const achados: string[] = [];
  for (const { segment } of SEGMENTADOR.segment(texto)) {
    if (REGEX_EMOJI.test(segment)) achados.push(segment);
  }
  return achados;
}

/**
 * Polaridade do emoji no Emoji Sentiment Ranking, a MESMA tabela que
 * `dolos/sinais/emoji.py` usa (exportada por `scripts/gerar_lexico_emoji.py`).
 *
 * Isto e exibicao de uma tabela publicada, nao atribuicao: quem diz o que
 * puxou a nota de um atendimento e `GET /conversas/{id}/atribuicao`.
 */
export function polaridadeDoEmoji(emoji: string): number {
  return POLARIDADE[emoji] ?? 0;
}

export type TermoDaClasse = {
  termo: string;
  ocorrencias: number;
  /** Quanto o termo e mais frequente NESTA classe do que no resto, em [-1, 1]. */
  distincao: number;
};

export type LexicoDaClasse = {
  categoria: Categoria;
  atendimentos: number;
  palavras: TermoDaClasse[];
  emojis: TermoDaClasse[];
};

function ranquear(
  porClasse: Map<Categoria, Map<string, number>>,
  categoria: Categoria,
  limite: number,
): TermoDaClasse[] {
  const daClasse = porClasse.get(categoria) ?? new Map<string, number>();
  const totalDaClasse = [...daClasse.values()].reduce((a, b) => a + b, 0);
  if (totalDaClasse === 0) return [];

  const outras = new Map<string, number>();
  let totalOutras = 0;
  for (const [outraCategoria, tabela] of porClasse) {
    if (outraCategoria === categoria) continue;
    for (const [termo, quantidade] of tabela) {
      outras.set(termo, (outras.get(termo) ?? 0) + quantidade);
      totalOutras += quantidade;
    }
  }

  return [...daClasse.entries()]
    .map(([termo, ocorrencias]) => {
      const pClasse = ocorrencias / totalDaClasse;
      const pOutras = totalOutras === 0 ? 0 : (outras.get(termo) ?? 0) / totalOutras;
      return { termo, ocorrencias, distincao: pClasse - pOutras };
    })
    .sort((a, b) => b.distincao - a.distincao || b.ocorrencias - a.ocorrencias)
    .slice(0, limite);
}

/**
 * Conta palavras e emojis das falas DO CLIENTE, agrupadas pela categoria que o
 * servidor atribuiu ao atendimento. Conversa sem score nao entra em classe
 * nenhuma -- ausencia de dado nao e uma quarta classe.
 */
export function lexicoPorClasse(detalhes: DetalheConversa[]): LexicoDaClasse[] {
  const palavrasPorClasse = new Map<Categoria, Map<string, number>>();
  const emojisPorClasse = new Map<Categoria, Map<string, number>>();
  const atendimentos = new Map<Categoria, number>();

  for (const conversa of detalhes) {
    const categoria = conversa.categoria;
    if (!categoria) continue;
    atendimentos.set(categoria, (atendimentos.get(categoria) ?? 0) + 1);

    const tabelaPalavras =
      palavrasPorClasse.get(categoria) ?? new Map<string, number>();
    const tabelaEmojis = emojisPorClasse.get(categoria) ?? new Map<string, number>();

    for (const mensagem of conversa.mensagens) {
      if (mensagem.autor !== "cliente") continue;
      for (const palavra of palavras(mensagem.texto)) {
        tabelaPalavras.set(palavra, (tabelaPalavras.get(palavra) ?? 0) + 1);
      }
      for (const emoji of emojisDoTexto(mensagem.texto)) {
        tabelaEmojis.set(emoji, (tabelaEmojis.get(emoji) ?? 0) + 1);
      }
    }

    palavrasPorClasse.set(categoria, tabelaPalavras);
    emojisPorClasse.set(categoria, tabelaEmojis);
  }

  return FAIXAS_NPS.map(({ categoria }) => ({
    categoria,
    atendimentos: atendimentos.get(categoria) ?? 0,
    palavras: ranquear(palavrasPorClasse, categoria, 6),
    emojis: ranquear(emojisPorClasse, categoria, 6),
  }));
}

// ---------------------------------------------------------------------------
// Atribuicao por sentenca (vem do servidor, nao e derivada aqui)
// ---------------------------------------------------------------------------

export type SentidoAtribuicao =
  | "puxou_para_baixo"
  | "puxou_para_cima"
  | "sem_inclinacao";

export type MarcaAtribuicao = {
  /** Indice da mensagem dentro de `conversa.mensagens`. */
  indice: number;
  sentido: SentidoAtribuicao;
  /** Classe mais provavel segundo o classificador. */
  classe: "insatisfeito" | "neutro" | "satisfeito";
  /** Probabilidade da classe mais provavel, em [0, 1]. */
  probabilidade: number;
  /** P(satisfeito) - P(insatisfeito): positivo puxa a nota para cima. */
  saldo: number;
  probInsatisfeito: number;
  probNeutro: number;
  probSatisfeito: number;
};

/**
 * A partir de qual saldo a fala e apresentada como tendo puxado a nota.
 *
 * Abaixo disso o classificador esta praticamente indiferente entre as duas
 * pontas, e chamar a frase de "a que derrubou a nota" seria ler ruido como
 * causa.
 */
export const LIMIAR_SALDO = 0.15;

const CLASSES = ["insatisfeito", "neutro", "satisfeito"] as const;

/**
 * Converte `GET /conversas/{id}/atribuicao` nas marcas da transcricao.
 *
 * NADA aqui e heuristica local: as probabilidades sao as do BERTimbau, uma por
 * mensagem, calculadas no servidor. A versao anterior desta tela marcava os
 * trechos por polaridade de emoji e tempo de espera porque o endpoint nao
 * existia; agora existe, e manter as duas seria manter duas fontes de verdade
 * para a mesma pergunta ("o que puxou a nota"). A anotacao de latencia
 * continua onde estava -- ela responde outra pergunta ("quanto o cliente
 * esperou") e sai dos timestamps, nao do classificador.
 *
 * Mensagem de bot/humano vem com probabilidade nula do servidor e nao vira
 * marca: ausencia de dado nao e inclinacao nenhuma.
 */
export function marcasDaAtribuicao(
  mensagens: MensagemAtribuida[],
): Map<number, MarcaAtribuicao> {
  const marcas = new Map<number, MarcaAtribuicao>();

  for (const mensagem of mensagens) {
    const { prob_insatisfeito, prob_neutro, prob_satisfeito } = mensagem;
    if (
      prob_insatisfeito === null ||
      prob_neutro === null ||
      prob_satisfeito === null
    ) {
      continue;
    }

    const probabilidades = [prob_insatisfeito, prob_neutro, prob_satisfeito];
    let melhor = 0;
    probabilidades.forEach((valor, indice) => {
      if (valor > probabilidades[melhor]) melhor = indice;
    });

    const saldo = prob_satisfeito - prob_insatisfeito;
    marcas.set(mensagem.indice, {
      indice: mensagem.indice,
      sentido:
        saldo <= -LIMIAR_SALDO
          ? "puxou_para_baixo"
          : saldo >= LIMIAR_SALDO
            ? "puxou_para_cima"
            : "sem_inclinacao",
      classe: CLASSES[melhor],
      probabilidade: probabilidades[melhor],
      saldo,
      probInsatisfeito: prob_insatisfeito,
      probNeutro: prob_neutro,
      probSatisfeito: prob_satisfeito,
    });
  }

  return marcas;
}

/** As falas que de fato inclinaram a nota, da mais decisiva para a menos. */
export function falasDecisivas(
  marcas: Map<number, MarcaAtribuicao>,
): MarcaAtribuicao[] {
  return [...marcas.values()]
    .filter((marca) => marca.sentido !== "sem_inclinacao")
    .sort((a, b) => Math.abs(b.saldo) - Math.abs(a.saldo));
}

// ---------------------------------------------------------------------------
// Importancia das features do fusor
// ---------------------------------------------------------------------------

export type SinalDaFeature = "texto" | "emoji" | "tempo";

const SINAL_POR_PREFIXO: [string, SinalDaFeature][] = [
  ["texto_", "texto"],
  ["emoji_", "emoji"],
];

/** A qual dos tres sinais a feature pertence -- tempo e o caso restante. */
export function sinalDaFeature(nome: string): SinalDaFeature {
  for (const [prefixo, sinal] of SINAL_POR_PREFIXO) {
    if (nome.startsWith(prefixo)) return sinal;
  }
  return "tempo";
}

export const ROTULO_SINAL: Record<SinalDaFeature, string> = {
  texto: "Texto",
  emoji: "Emoji",
  tempo: "Tempo",
};

export type PesoDoSinal = {
  sinal: SinalDaFeature;
  /** Soma dos pesos absolutos das features do sinal, normalizada em [0, 1]. */
  fracao: number;
};

/**
 * Agrega as 16 importancias do fusor nos TRES sinais do trabalho.
 *
 * O peso e o coeficiente absoluto medio da regressao logistica -- e por isso
 * que o fusor e linear: a pergunta "qual sinal pesou mais" tem resposta.
 */
export function pesoPorSinal(
  importancias: Record<string, number>,
): PesoDoSinal[] {
  const soma = new Map<SinalDaFeature, number>();
  let total = 0;

  for (const [nome, peso] of Object.entries(importancias)) {
    const sinal = sinalDaFeature(nome);
    const absoluto = Math.abs(peso);
    soma.set(sinal, (soma.get(sinal) ?? 0) + absoluto);
    total += absoluto;
  }

  return (["texto", "emoji", "tempo"] as SinalDaFeature[]).map((sinal) => ({
    sinal,
    fracao: total === 0 ? 0 : (soma.get(sinal) ?? 0) / total,
  }));
}

// ---------------------------------------------------------------------------
// Tempo mediano de resposta do conjunto
// ---------------------------------------------------------------------------

export function tempoMedianoDeResposta(detalhes: DetalheConversa[]): number | null {
  const todas = detalhes.flatMap((conversa) =>
    latenciasAnotadas(conversa.mensagens).map((l) => l.segundos),
  );
  return mediana(todas);
}
