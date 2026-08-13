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

export function notaDeScore(score: number): number {
  return Math.round(Math.min(100, Math.max(0, score)) / 10);
}

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
 * Faixas de latencia calibradas pela literatura de live chat que o proprio
 * projeto cita: pico de satisfacao em 5-10s, degradacao acima de 1min,
 * abandono acima de 3min.
 */
export function severidadeLatencia(segundos: number): "boa" | "atencao" | "critica" {
  if (segundos <= 30) return "boa";
  if (segundos <= 60) return "atencao";
  return "critica";
}

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
    if (resumo.score === null) {
      semSinal += 1;
      continue;
    }
    contagem[notaDeScore(resumo.score)] += 1;
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

const REGEX_EMOJI = /\p{Extended_Pictographic}/gu;

export function emojisDoTexto(texto: string): string[] {
  return texto.match(REGEX_EMOJI) ?? [];
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
 * transcricao: a polaridade dos emojis (mesmo lexicon do sinal de emoji) e o
 * tempo de espera do cliente (mesma regra do sinal de tempo).
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

  for (const { indice, segundos } of latenciasAnotadas(conversa.mensagens)) {
    const severidade = severidadeLatencia(segundos);
    if (severidade === "boa") continue;
    evidencias.push({
      indice,
      tipo: "espera",
      sentido: "puxou_para_baixo",
      rotulo: severidade === "critica" ? "Espera crítica" : "Espera longa",
      detalhe:
        severidade === "critica"
          ? "acima de 1 min — faixa de abandono na literatura de live chat"
          : "entre 30 s e 1 min — fora do pico de satisfação (5–10 s)",
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
