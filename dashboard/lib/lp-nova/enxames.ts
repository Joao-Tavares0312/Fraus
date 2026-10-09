import { FAMILIAS_DO_VETOR, FATOS_DO_MODELO } from "../../components/lp/fatos";

/**
 * OS ENXAMES DO FUSOR: quantas particulas cada familia de sinal recebe.
 *
 * A quantidade e DADO, nao enfeite -- a mesma regra da constelacao da vitrine.
 * Tempo tem 7 das 39 features, entao tem 7/39 das particulas; quem contar o
 * enxame le a proporcao real do vetor. A conta fecha por maior resto, para a
 * soma bater exatamente com o buffer que a GPU aloca.
 */
export type Enxame = {
  chave: string;
  qtd: number;
  /** Indice da primeira particula do enxame no storage buffer. */
  inicio: number;
  particulas: number;
  /** Centro do enxame em coordenadas de tela normalizadas [0, 1]. */
  centro: [number, number];
};

const RAIO = 0.32;

export function distribuirEnxames(total: number): Enxame[] {
  const features = FATOS_DO_MODELO.features;
  const cotas = FAMILIAS_DO_VETOR.map((f) => (total * f.qtd) / features);
  const inteiros = cotas.map(Math.floor);
  let faltam = total - inteiros.reduce((a, b) => a + b, 0);
  const porResto = cotas
    .map((cota, indice) => ({ indice, resto: cota - Math.floor(cota) }))
    .sort((a, b) => b.resto - a.resto);
  for (const { indice } of porResto) {
    if (faltam === 0) break;
    inteiros[indice] += 1;
    faltam -= 1;
  }
  if (inteiros.some((n) => n === 0)) {
    throw new RangeError(
      `${total} particulas nao cobrem as ${FAMILIAS_DO_VETOR.length} familias: um enxame vazio mentiria a contagem`,
    );
  }

  let inicio = 0;
  return FAMILIAS_DO_VETOR.map((f, indice) => {
    const angulo = -Math.PI / 2 + (indice / FAMILIAS_DO_VETOR.length) * Math.PI * 2;
    const enxame: Enxame = {
      chave: f.chave,
      qtd: f.qtd,
      inicio,
      particulas: inteiros[indice],
      centro: [0.5 + RAIO * Math.cos(angulo), 0.5 + RAIO * Math.sin(angulo)],
    };
    inicio += inteiros[indice];
    return enxame;
  });
}
