/**
 * Filtro de periodo GLOBAL da interface.
 *
 * A interface fala em "o periodo" o tempo todo. Ate agora era texto prometendo
 * o que nao existia. O periodo vive na URL (`?de=&ate=`, datas AAAA-MM-DD
 * inclusivas) por tres razoes:
 *
 *   1. os componentes de pagina sao de SERVIDOR e leem `searchParams` sem
 *      precisar de estado global no cliente;
 *   2. o recorte fica compartilhavel e sobrevive a um F5 -- numa banca, mandar
 *      o link ja com o periodo certo importa;
 *   3. so existe UM lugar onde o recorte esta escrito, entao indicador,
 *      grafico, tabela e export nunca divergem entre si.
 *
 * A API do Fraus NAO recebe filtro de data em nenhuma rota, entao o corte
 * acontece no cliente sobre `iniciada_em`. Um `GET /conversas?de=&ate=` (e o
 * mesmo par em `/indicadores`) tornaria isso server-side e evitaria baixar o
 * banco inteiro para descartar a maior parte -- esta anotado no relatorio.
 */

import { diaDoProduto } from "./fuso";
import type { ResumoConversa } from "./api";

export type Periodo = {
  /** AAAA-MM-DD inclusivo, ou null para "sem limite inferior". */
  de: string | null;
  /** AAAA-MM-DD inclusivo, ou null para "sem limite superior". */
  ate: string | null;
};

export const PERIODO_TOTAL: Periodo = { de: null, ate: null };

const FORMATO_DIA = /^\d{4}-\d{2}-\d{2}$/;

function normalizar(valor: string | string[] | undefined): string | null {
  const bruto = Array.isArray(valor) ? valor[0] : valor;
  if (!bruto || !FORMATO_DIA.test(bruto)) return null;
  return bruto;
}

/** Le o periodo dos `searchParams` de uma pagina. Valor invalido vira null. */
export function lerPeriodo(
  parametros: Record<string, string | string[] | undefined>,
): Periodo {
  const de = normalizar(parametros.de);
  const ate = normalizar(parametros.ate);
  // Intervalo invertido seria um recorte vazio silencioso; trocar as pontas e
  // o comportamento que o usuario quis dizer.
  if (de && ate && de > ate) return { de: ate, ate: de };
  return { de, ate };
}

export function periodoEstaAtivo(periodo: Periodo): boolean {
  return periodo.de !== null || periodo.ate !== null;
}

/**
 * Dia (AAAA-MM-DD) de um timestamp ISO, no fuso do produto.
 *
 * O nome ficou de quando era o dia do navegador. Quem opera pensa em "dia 12"
 * de Brasilia, e a API recorta e agrupa pelo mesmo dia (`fraus/fuso.py`).
 */
export function diaLocal(iso: string): string {
  return diaDoProduto(iso);
}

export function dentroDoPeriodo(iso: string, periodo: Periodo): boolean {
  const dia = diaLocal(iso);
  if (periodo.de && dia < periodo.de) return false;
  if (periodo.ate && dia > periodo.ate) return false;
  return true;
}

export function filtrarPorPeriodo<T extends { iniciada_em: string }>(
  itens: T[],
  periodo: Periodo,
): T[] {
  if (!periodoEstaAtivo(periodo)) return itens;
  return itens.filter((item) => dentroDoPeriodo(item.iniciada_em, periodo));
}

export type Extensao = { primeiro: string; ultimo: string } | null;

/** Primeiro e ultimo dia COM dado. Base honesta para os atalhos de periodo. */
export function extensaoDosDados(conversas: ResumoConversa[]): Extensao {
  if (conversas.length === 0) return null;
  const dias = conversas.map((c) => diaLocal(c.iniciada_em)).sort();
  return { primeiro: dias[0], ultimo: dias[dias.length - 1] };
}

/** Soma dias a um AAAA-MM-DD, em UTC, para nao tropecar em horario de verao. */
export function somarDias(dia: string, delta: number): string {
  const [ano, mes, numero] = dia.split("-").map(Number);
  const data = new Date(Date.UTC(ano, mes - 1, numero));
  data.setUTCDate(data.getUTCDate() + delta);
  return data.toISOString().slice(0, 10);
}

export function formatarDia(dia: string): string {
  const [ano, mes, numero] = dia.split("-");
  return `${numero}/${mes}/${ano}`;
}

/**
 * Como o periodo aparece escrito na interface.
 *
 * Sem filtro o rotulo NAO e "todo o periodo" e ponto: ele diz de que dia a que
 * dia o dado realmente vai. "O periodo" sem extensao declarada e a mesma
 * vagueza que o produto existe para combater.
 */
export function rotuloPeriodo(periodo: Periodo, extensao: Extensao): string {
  if (!periodoEstaAtivo(periodo)) {
    return extensao
      ? `todo o período (${formatarDia(extensao.primeiro)} – ${formatarDia(extensao.ultimo)})`
      : "todo o período";
  }
  if (periodo.de && periodo.ate) {
    return `${formatarDia(periodo.de)} – ${formatarDia(periodo.ate)}`;
  }
  if (periodo.de) return `de ${formatarDia(periodo.de)} em diante`;
  return `até ${formatarDia(periodo.ate as string)}`;
}

/** Serializa o periodo de volta para query string (para links da navegacao). */
export function paraQuery(periodo: Periodo): string {
  const parametros = new URLSearchParams();
  if (periodo.de) parametros.set("de", periodo.de);
  if (periodo.ate) parametros.set("ate", periodo.ate);
  const texto = parametros.toString();
  return texto ? `?${texto}` : "";
}
