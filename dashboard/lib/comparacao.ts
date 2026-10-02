/**
 * Apresentacao do laudo de comparacao (BERTimbau x Laya) -- a parte pura.
 *
 * Nada aqui calcula metrica: acuracia, F1, intervalo e o proprio
 * `diferenca_demonstrada` vem prontos do servidor, que os leu do laudo do
 * notebook 07. Este arquivo so decide COMO escrever o numero que chegou, e
 * que frase dizer sobre uma comparacao que o servidor ja julgou.
 */

import type { ComparacaoDoConjunto } from "./api";

const TRES_CASAS = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});
const UMA_CASA = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const INTEIRO = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

/** Metrica em [0,1] com tres casas FIXAS: coluna de tabela precisa alinhar. */
export function fracao(valor: number | null): string {
  return valor === null ? "—" : TRES_CASAS.format(valor);
}

/** Diferenca entre modelos: o sinal e a informacao, entao sempre aparece. */
export function comSinal(valor: number): string {
  return `${valor < 0 ? "−" : "+"}${TRES_CASAS.format(Math.abs(valor))}`;
}

export function milissegundos(valor: number | null): string {
  if (valor === null) return "—";
  return `${valor >= 10 ? INTEIRO.format(valor) : UMA_CASA.format(valor)} ms`;
}

/**
 * A frase da comparacao. Intervalo que contem o zero nao nomeia vencedor --
 * e quem decide isso e o servidor (`diferenca_demonstrada`), nao esta funcao.
 */
export function veredito(
  comparacao: ComparacaoDoConjunto,
  nomes: Record<string, string>,
): string {
  if (!comparacao.diferenca_demonstrada) return "sem diferença demonstrada";
  const chave =
    comparacao.diferenca_f1_macro > 0 ? comparacao.candidato : comparacao.referencia;
  return `${nomes[chave] ?? chave} à frente`;
}

const QUATRO_CASAS = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 4,
  maximumFractionDigits: 4,
});

/** p muito pequeno nao vira "0,0000": zero seria afirmar certeza. */
export function pValor(valor: number): string {
  return valor < 0.0001 ? "p < 0,0001" : `p = ${QUATRO_CASAS.format(valor)}`;
}
