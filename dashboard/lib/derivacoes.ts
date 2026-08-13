/**
 * Derivacoes feitas no cliente da API a partir do que os endpoints DAO.
 *
 * A API do Dolos expoe indicadores agregados, a lista de conversas e a
 * transcricao. Ela NAO expoe serie temporal, latencia agregada, lexico por
 * classe nem atribuicao por sentenca. Tudo que este arquivo calcula sai dos
 * timestamps e do texto que a transcricao ja entrega -- nada aqui inventa
 * numero. O que nao da para derivar honestamente nao esta aqui: esta como
 * estado vazio na interface, nomeando o endpoint que resolveria.
 *
 * A regra de latencia e a MESMA de `dolos/sinais/tempo.py`: o intervalo de
 * cada mensagem do cliente ate a proxima resposta (bot ou humano).
 */

import lexicoEmoji from "./lexicoEmoji.json";
import type { Categoria, DetalheConversa, Mensagem, ResumoConversa } from "./api";

const RESPONDENTES = new Set(["bot", "humano"]);
const LIMIAR_POLARIDADE = 0.1;
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
// Evidencias observaveis no atendimento
// ---------------------------------------------------------------------------

export type Evidencia = {
  indice: number;
  tipo: "emoji" | "espera";
  sentido: "puxou_para_baixo" | "puxou_para_cima";
  rotulo: string;
  detalhe: string;
};

/**
 * Marca os trechos que puxaram a nota USANDO SO O QUE E OBSERVAVEL na
 * transcricao: a polaridade dos emojis e o tempo de espera do cliente.
 *
 * O que e compartilhado com `dolos/sinais/emoji.py` e a TABELA de polaridade
 * (Emoji Sentiment Ranking, exportada para `lexicoEmoji.json`) E o recorte,
 * que aqui e feito por cluster de grafema para casar com `emoji.emoji_list`.
 * O que NAO e compartilhado: o motor usa tambem a posicao relativa do emoji
 * na mensagem como feature -- a interface so mostra a polaridade media.
 * A regra de espera e a mesma do sinal de tempo.
 *
 * O terceiro sinal -- a probabilidade por mensagem do classificador de texto,
 * que e calculada na Task 7 -- NAO tem endpoint, entao nao aparece aqui e nem
 * e simulado. A interface diz isso em voz alta em vez de fingir atribuicao.
 */
export function evidenciasDaConversa(conversa: DetalheConversa): Evidencia[] {
  const evidencias: Evidencia[] = [];

  conversa.mensagens.forEach((mensagem, indice) => {
    if (mensagem.autor !== "cliente") return;
    const emojis = emojisDoTexto(mensagem.texto);
    if (emojis.length === 0) return;
    const soma = emojis.reduce((total, e) => total + polaridadeDoEmoji(e), 0);
    const media = soma / emojis.length;
    if (Math.abs(media) < LIMIAR_POLARIDADE) return;
    evidencias.push({
      indice,
      tipo: "emoji",
      sentido: media < 0 ? "puxou_para_baixo" : "puxou_para_cima",
      rotulo: media < 0 ? "Emoji negativo" : "Emoji positivo",
      detalhe: `${emojis.join(" ")} · polaridade ${media > 0 ? "+" : ""}${media.toFixed(2)} no Emoji Sentiment Ranking`,
    });
  });

  // So espera que a literatura associa a PERDA vira evidencia: abaixo de 1 min
  // a resposta esta no saudavel e marcar isso seria inventar problema.
  for (const { indice, segundos } of latenciasAnotadas(conversa.mensagens)) {
    const severidade = severidadeLatencia(segundos);
    if (severidade === "pico" || severidade === "saudavel") continue;
    evidencias.push({
      indice,
      tipo: "espera",
      sentido: "puxou_para_baixo",
      rotulo: ROTULO_LATENCIA[severidade].titulo,
      detalhe: ROTULO_LATENCIA[severidade].detalhe,
    });
  }

  return evidencias.sort((a, b) => a.indice - b.indice);
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
