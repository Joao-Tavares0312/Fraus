/**
 * A fila de anotacao da regua de ironia, sem React.
 *
 * Quem anota nao tem conta: so um link com token opaco. A ORDEM das frases e
 * o servidor que decide (embaralhada por anotador, sem os dois lados de um par
 * vizinhos) -- aqui ela nunca e reordenada. Esta maquina de estado e pura de
 * proposito: "so avanca depois do 201" e "erro mantem a frase" sao regras que
 * erram em silencio e o build nao pega.
 */

export type Resposta = "ironico" | "nao_ironico" | "contexto";
export type Frase = { id: string; texto: string };
export type Respostas = Record<string, Resposta>;

export type Falha =
  | { tipo: "rede" }
  | { tipo: "limite"; segundos: number | null }
  | { tipo: "http"; status: number };

export type EstadoDaFila = {
  frases: readonly Frase[];
  respostas: Respostas;
  pos: number;
  enviando: boolean;
  erro: string | null;
};

/** Mesmo formato do token gerado pela API (`secrets.token_urlsafe(32)`). */
export function tokenDeAnotador(valor: unknown): string | null {
  return typeof valor === "string" && /^[A-Za-z0-9_-]{43}$/.test(valor) ? valor : null;
}

function primeiraSemResposta(frases: readonly Frase[], respostas: Respostas): number {
  const i = frases.findIndex((f) => !respostas[f.id]);
  return i === -1 ? frases.length : i;
}

export function estadoDaFila(frases: readonly Frase[], respostas: Respostas): EstadoDaFila {
  // Resposta de frase que nao esta na fila nao conta: nao deve mexer no "faltam".
  const ids = new Set(frases.map((f) => f.id));
  const validas: Respostas = {};
  for (const [id, r] of Object.entries(respostas)) if (ids.has(id)) validas[id] = r;
  return { frases, respostas: validas, pos: primeiraSemResposta(frases, validas), enviando: false, erro: null };
}

export function faltam(e: EstadoDaFila): number {
  return e.frases.length - Object.keys(e.respostas).length;
}

export function mensagemDeFalha(f: Falha): string {
  const base = "Sua resposta NÃO foi registrada.";
  if (f.tipo === "limite") return `${base} Muitas respostas seguidas: aguarde alguns segundos e tente de novo.`;
  if (f.tipo === "rede") return `${base} Não consegui falar com o servidor. Confira a conexão e tente de novo.`;
  return `${base} O servidor recusou o envio (erro ${f.status}). Tente de novo.`;
}

export function fila(e: EstadoDaFila) {
  const fim = e.pos >= e.frases.length;
  return {
    fim,
    podeResponder: !fim && !e.enviando,
    podeVoltar: e.pos > 0 && !e.enviando,
    /** Comeca um envio. Sem efeito (mesmo objeto) se ja ha um em andamento ou se acabou. */
    enviar(): EstadoDaFila {
      return fim || e.enviando ? e : { ...e, enviando: true, erro: null };
    },
    /** So aqui, depois do 201, a resposta entra e a fila anda. */
    sucesso(fraseId: string, resposta: Resposta): EstadoDaFila {
      const respostas = { ...e.respostas, [fraseId]: resposta };
      return { ...e, respostas, enviando: false, erro: null, pos: primeiraSemResposta(e.frases, respostas) };
    },
    /** A frase fica onde esta e nada e gravado. */
    falha(f: Falha): EstadoDaFila {
      return { ...e, enviando: false, erro: mensagemDeFalha(f) };
    },
    voltar(): EstadoDaFila {
      return e.pos > 0 && !e.enviando ? { ...e, pos: e.pos - 1, erro: null } : e;
    },
  };
}

type EventoDeTecla = { key: string; repeat: boolean; ctrlKey: boolean; metaKey: boolean; altKey: boolean };
const TECLAS: Record<string, Resposta> = { "1": "ironico", "2": "nao_ironico", "3": "contexto" };

export function respostaDaTecla(ev: EventoDeTecla): Resposta | null {
  if (ev.repeat || ev.ctrlKey || ev.metaKey || ev.altKey) return null;
  return TECLAS[ev.key] ?? null;
}

type Buscar = (url: string, init?: RequestInit) => Promise<Response>;
const BASE = "/api/fraus/anotacao";

export async function enviarResposta(
  token: string,
  fraseId: string,
  resposta: Resposta,
  buscar: Buscar = (u, i) => fetch(u, i),
): Promise<{ ok: true } | { ok: false; falha: Falha }> {
  try {
    const r = await buscar(`${BASE}/${token}/respostas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frase_id: fraseId, resposta }),
    });
    if (r.status === 201) return { ok: true };
    if (r.status === 429) {
      const s = Number(r.headers.get("Retry-After"));
      return { ok: false, falha: { tipo: "limite", segundos: Number.isFinite(s) && s > 0 ? s : null } };
    }
    return { ok: false, falha: { tipo: "http", status: r.status } };
  } catch {
    return { ok: false, falha: { tipo: "rede" } };
  }
}

export type Carga =
  | { tipo: "ok"; frases: Frase[]; respostas: Respostas }
  | { tipo: "invalido" }
  | { tipo: "erro" };

export async function carregarFila(token: string, buscar: Buscar = (u, i) => fetch(u, i)): Promise<Carga> {
  try {
    const r = await buscar(`${BASE}/${token}`, { cache: "no-store" });
    if (r.status === 404) return { tipo: "invalido" };
    if (!r.ok) return { tipo: "erro" };
    const corpo = (await r.json()) as { frases?: unknown; respostas?: unknown };
    if (!Array.isArray(corpo.frases) || corpo.frases.length === 0) return { tipo: "erro" };
    const frases = corpo.frases.map((f: { id: string; texto: string }) => ({ id: String(f.id), texto: String(f.texto) }));
    const respostas = corpo.respostas && typeof corpo.respostas === "object" ? (corpo.respostas as Respostas) : {};
    return { tipo: "ok", frases, respostas };
  } catch {
    return { tipo: "erro" };
  }
}
