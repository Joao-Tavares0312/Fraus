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

/**
 * A ordem das sete emocoes NA PAUTA: as negativas agrupadas, depois surpresa,
 * alegria, e neutro por ultimo.
 *
 * Nao e a ordem do modelo (`fraus/sinais/emocao.py`) -- e uma ordem de LEITURA
 * que tambem e condicao de legibilidade: cada emocao tem cor propria (tokens
 * `--emo-*` no globals.css), e a paleta foi validada para daltonismo e visao
 * normal comparando VIZINHOS nesta sequencia exata. Das 5040 ordens possiveis,
 * 78 passam; a ordem do modelo nao passa. Mudar isto exige rodar o validador.
 */
export const ORDEM_EMOCOES = [
  "medo",
  "nojo",
  "tristeza",
  "raiva",
  "surpresa",
  "alegria",
  "neutro",
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
export function separarEmocoes(emocao: Record<string, number>, visiveis = EMOCOES_VISIVEIS) {
  const quantas = visiveis;
  const treinadas = Object.entries(emocao).filter(([nome]) => nome !== "desprezo");
  const nomesVisiveis = new Set(
    [...treinadas].sort((a, b) => b[1] - a[1]).slice(0, quantas).map(([nome]) => nome),
  );
  const posicao = (nome: string) => {
    const indice = (ORDEM_EMOCOES as readonly string[]).indexOf(nome);
    return indice === -1 ? ORDEM_EMOCOES.length : indice;
  };
  const porOrdemCanonica = (a: [string, number], b: [string, number]) => posicao(a[0]) - posicao(b[0]);
  const recolhidas = treinadas.filter(([nome]) => !nomesVisiveis.has(nome)).sort(porOrdemCanonica);
  // Com TODAS a vista (quantas >= 7) a ordem e a canonica, nao a de valor: o
  // olho aprende onde fica cada emocao. Com duas, sao as maiores, da maior.
  const aVista = treinadas.filter(([nome]) => nomesVisiveis.has(nome));
  const ordenadasAVista =
    quantas >= ORDEM_EMOCOES.length ? aVista.sort(porOrdemCanonica) : aVista.sort((a, b) => b[1] - a[1]);
  return {
    visiveis: ordenadasAVista,
    recolhidas,
    desprezo: "desprezo" in emocao ? emocao.desprezo : null,
  };
}
