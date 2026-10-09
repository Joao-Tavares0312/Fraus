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

const NAO_GRAVADAS = "leituras ainda não gravadas — rode scripts/gravar_leituras_lp.py contra a API de produção";

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
