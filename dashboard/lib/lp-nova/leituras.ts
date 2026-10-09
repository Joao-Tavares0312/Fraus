import type { MensagemAtribuida } from "../api";

/**
 * AS LEITURAS GRAVADAS da LP nova: o que o motor REAL de producao disse sobre
 * cinco conversas sinteticas, gravado por `scripts/gravar_leituras_lp.py`.
 *
 * A pagina nao calcula nada (invariante 3): score, nota, categoria e as
 * probabilidades por mensagem chegam prontos daqui. Este modulo so confere
 * que o arquivo e o que diz ser -- e, quando ele nao existe ou nao fecha,
 * devolve o que falta em palavras, para a tela mostrar o estado vazio em vez
 * de uma leitura inventada.
 */
export const IDS_LEITURAS = ["obrigado", "ironia", "espera", "promotor", "sem-sinal"] as const;
export type IdLeitura = (typeof IDS_LEITURAS)[number];

const SEM_CLIENTE: IdLeitura = "sem-sinal";

export type MensagemDaConversa = { autor: "cliente" | "bot" | "humano"; texto: string; enviada_em: string };

export type Leitura = {
  id: IdLeitura;
  score: number | null;
  nota: number | null;
  categoria: string | null;
  motivo_sem_sinal: string | null;
  mensagens: MensagemAtribuida[];
  contribuicoes: unknown[];
  conversa: { id: string; mensagens: MensagemDaConversa[] };
  sha256: string;
};

export type Procedencia = { gravado_em: string; api: string; modelo: string };
export type ConjuntoLeituras = { procedencia: Procedencia; leituras: Leitura[] };
export type Falta = { falta: string };

// Para o VISITANTE: o que falta, sem instrucao de desenvolvedor na pagina
// publica. Como resolver mora em docs/handoff.md (scripts/gravar_leituras_lp.py).
const NAO_GRAVADAS = "As leituras desta seção ainda não foram gravadas pelo motor de produção";

function texto(v: unknown): v is string {
  return typeof v === "string" && v.length > 0;
}

export function validarLeituras(bruto: unknown): ConjuntoLeituras | Falta {
  if (bruto === null || typeof bruto !== "object") return { falta: NAO_GRAVADAS };
  const { procedencia, leituras } = bruto as Partial<ConjuntoLeituras>;
  if (!procedencia || !texto(procedencia.gravado_em) || !texto(procedencia.api) || !texto(procedencia.modelo)) {
    return { falta: "procedência incompleta: sem data, API e modelo a leitura não tem lastro" };
  }
  if (!Array.isArray(leituras)) return { falta: NAO_GRAVADAS };

  const porId = new Map(leituras.map((l) => [l.id, l]));
  const ordenadas: Leitura[] = [];
  for (const id of IDS_LEITURAS) {
    const l = porId.get(id);
    if (!l) return { falta: `falta a leitura ${id}` };
    const semNota = l.score === null;
    if (id === SEM_CLIENTE && !semNota) return { falta: `${id} voltou com nota: conversa sem cliente não tem nota` };
    if (id !== SEM_CLIENTE && semNota) return { falta: `${id} voltou sem nota: motor errado na gravação` };
    ordenadas.push(l);
  }
  return { procedencia, leituras: ordenadas };
}

/** Data da gravacao no fuso do produto: servidor (UTC) e navegador concordam. */
export function dataDaGravacao(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "America/Sao_Paulo",
  }).format(new Date(iso));
}

/**
 * O que o ROTEIRO de cada conversa sintetica encena -- escrito por nos, nao
 * medido. A pagina compara com a categoria que o motor gravou e, quando
 * discordam, DIZ que o Fraus leu diferente: esconder o erro seria escolher a
 * leitura a dedo.
 */
export const ROTEIRO: Record<IdLeitura, string | null> = {
  obrigado: "detrator",
  ironia: "detrator",
  espera: "detrator",
  promotor: "promotor",
  "sem-sinal": null,
};

export function concordaComRoteiro(l: { id: IdLeitura; categoria: string | null }): boolean {
  return ROTEIRO[l.id] === l.categoria;
}
