/** Formatacao pt-BR. Uma unica fonte para que nenhum numero apareça com duas caras. */

export const ROTULO_SEM_SINAL = "sem sinal";

const NUMERO = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const INTEIRO = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

/**
 * Numero em pt-BR com `casas` decimais no maximo.
 *
 * Os dois formatadores mais usados (0 e 1 casa) sao memoizados no modulo
 * porque `Intl.NumberFormat` e caro e a tabela chama isto por celula.
 */
const CACHE_FORMATADOR = new Map<number, Intl.NumberFormat>();

export function formatarNumero(valor: number, casas = 1): string {
  if (casas === 0) return INTEIRO.format(valor);
  if (casas === 1) return NUMERO.format(valor);
  let formatador = CACHE_FORMATADOR.get(casas);
  if (!formatador) {
    formatador = new Intl.NumberFormat("pt-BR", {
      maximumFractionDigits: casas,
    });
    CACHE_FORMATADOR.set(casas, formatador);
  }
  return formatador.format(valor);
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

/**
 * Tempo de espera, ou o travessão quando ele NAO EXISTIU.
 *
 * O nulo tem que virar traço, nunca "0 s": zero numa coluna de tempo de
 * resposta se le como "respondeu na hora", e a conversa que nunca teve
 * atendente humano apareceria como a mais agil da operacao. O travessao diz a
 * verdade -- nao houve essa espera para medir.
 */
export function formatarEsperaOuTraco(segundos: number | null): string {
  return segundos === null ? "—" : formatarSegundos(segundos);
}

/**
 * Como o atendimento terminou. Conjunto fechado, definido em `fraus.resumo`.
 *
 * "Encerrada" nao afirma que o problema foi resolvido -- afirma que a conversa
 * fechou, que e o unico fato que o dado sustenta.
 */
export const ROTULO_DESFECHO: Record<string, string> = {
  sem_sinal: "Sem sinal",
  escalada: "Escalada",
  sem_resposta: "Sem resposta",
  encerrada: "Encerrada",
  em_aberto: "Em aberto",
};

/** O que cada desfecho quer dizer, para o `title` e a legenda da tela. */
export const EXPLICACAO_DESFECHO: Record<string, string> = {
  sem_sinal: "O cliente não falou. Não há atendimento a avaliar.",
  escalada: "Passou para atendente humano.",
  sem_resposta: "A última fala é do cliente e ninguém respondeu.",
  encerrada: "A conversa fechou com o atendimento respondendo por último.",
  em_aberto: "Sem registro de encerramento.",
};

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
