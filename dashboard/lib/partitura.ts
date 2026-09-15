/**
 * A logica da PARTITURA DA FALA -- a leitura por frase desenhada numa pauta.
 *
 * Fica fora do componente para poder ser testada: duas decisoes daqui mudam o
 * que o analista le. QUANDO a disputa acende, e QUAIS emocoes ficam a vista.
 */

/** Ordem fixa das classes: 0 insatisfeito, 1 neutro, 2 satisfeito (invariante 8). */
export const ORDEM_CLASSES = ["insatisfeito", "neutro", "satisfeito"] as const;
export type Classe = (typeof ORDEM_CLASSES)[number];
export type ProbabilidadesDeClasse = Record<Classe, number>;

/**
 * Margem abaixo da qual a 1a e a 2a classe estao "em disputa".
 *
 * NUMERO DE INTERFACE, SEM PROCEDENCIA MEDIDA -- aprovado em 15/09/2026 na
 * comparacao de desenhos, e declarado assim para ninguem cita-lo como
 * calibracao. O que ele mede e DISTANCIA entre duas probabilidades, nunca
 * "confianca": o modelo nao e calibrado, e chamar isso de confianca
 * prometeria o que ele nao entrega.
 */
export const LIMIAR_DISPUTA = 0.15;

/** A ordem canonica das sete classes treinadas de emocao (`fraus/sinais/emocao.py`). */
export const ORDEM_EMOCOES = [
  "alegria",
  "surpresa",
  "neutro",
  "tristeza",
  "medo",
  "raiva",
  "nojo",
] as const;

/**
 * Probabilidade como a pauta escreve: ",87", "1,00". Uma funcao so para a
 * pauta e o resumo recolhido da fala -- "0.98" num e ",98" no outro, lado a
 * lado, era a mesma leitura escrita de dois jeitos.
 */
export function formatarProbabilidade(valor: number): string {
  return valor >= 0.995 ? "1,00" : valor.toFixed(2).replace("0.", ",");
}

/** Quantas emocoes ficam a vista antes do "ver mais". */
export const EMOCOES_VISIVEIS = 2;

/** Tolerancia de ponto flutuante: 0,575 - 0,425 da 0,14999..., nao 0,15. */
const TOLERANCIA = 1e-9;

export function disputaDasClasses(classes: ProbabilidadesDeClasse) {
  // Empate exato fica com a classe de MENOR indice, sempre: sortear faria a
  // mesma fala mudar de vencedora ao recarregar.
  const [vencedora, segunda] = ORDEM_CLASSES.map((nome, indice) => ({
    nome,
    valor: classes[nome],
    indice,
  })).sort((a, b) => b.valor - a.valor || a.indice - b.indice);
  const margem = vencedora.valor - segunda.valor;
  return {
    vencedora: vencedora.nome,
    segunda: segunda.nome,
    margem,
    disputa: margem < LIMIAR_DISPUTA - TOLERANCIA,
  };
}

/**
 * As emocoes que ficam a vista e as que recolhem.
 *
 * `desprezo` NUNCA disputa as visiveis: nao e classe treinada, e a diade raiva
 * + nojo (ver `CabecasDeLeitura`). Ele sai a parte, e ausente e `null` --
 * nunca 0, que leria como "medido e zerado" (invariante 2).
 */
export function separarEmocoes(emocao: Record<string, number>) {
  const treinadas = Object.entries(emocao).filter(([nome]) => nome !== "desprezo");
  const visiveis = [...treinadas].sort((a, b) => b[1] - a[1]).slice(0, EMOCOES_VISIVEIS);
  const nomesVisiveis = new Set(visiveis.map(([nome]) => nome));
  const posicao = (nome: string) => {
    const indice = (ORDEM_EMOCOES as readonly string[]).indexOf(nome);
    return indice === -1 ? ORDEM_EMOCOES.length : indice;
  };
  const recolhidas = treinadas
    .filter(([nome]) => !nomesVisiveis.has(nome))
    .sort((a, b) => posicao(a[0]) - posicao(b[0]));
  return {
    visiveis,
    recolhidas,
    desprezo: "desprezo" in emocao ? emocao.desprezo : null,
  };
}
