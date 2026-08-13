/** Formatacao pt-BR. Uma unica fonte para que nenhum numero apareça com duas caras. */

export const ROTULO_SEM_SINAL = "sem sinal";

const NUMERO = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const INTEIRO = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

export function formatarNumero(valor: number, casas = 1): string {
  return casas === 0 ? INTEIRO.format(valor) : NUMERO.format(valor);
}

export function formatarPercentual(valor: number): string {
  return `${NUMERO.format(valor)}%`;
}

/** NPS vive em [-100, 100]: o sinal e informacao, entao sempre aparece. */
export function formatarNps(valor: number): string {
  const arredondado = Math.round(valor * 10) / 10;
  const sinal = arredondado > 0 ? "+" : "";
  return `${sinal}${NUMERO.format(arredondado)}`;
}

export function formatarSegundos(segundos: number): string {
  if (segundos < 60) return `${NUMERO.format(segundos)} s`;
  const minutos = Math.floor(segundos / 60);
  const resto = Math.round(segundos % 60);
  if (minutos < 60) return resto === 0 ? `${minutos} min` : `${minutos} min ${resto} s`;
  const horas = Math.floor(minutos / 60);
  return `${horas} h ${minutos % 60} min`;
}

export function formatarDataHora(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatarData(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function formatarHora(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/** Rotulo curto de eixo: 05/08 */
export function formatarDiaCurto(dia: string): string {
  const [, mes, resto] = dia.split("-");
  return `${resto}/${mes}`;
}

export const ROTULO_CATEGORIA: Record<string, string> = {
  detrator: "Detrator",
  neutro: "Neutro",
  promotor: "Promotor",
};

export const ROTULO_AUTOR: Record<string, string> = {
  cliente: "Cliente",
  bot: "Bot",
  humano: "Atendente",
};
