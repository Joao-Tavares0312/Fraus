/** Ceu da LP: pontos e riscos gerados por uma PRNG com semente, para que o
 * servidor e o teste vejam sempre o mesmo ceu (nada de Math.random no render).
 * x/y em %, tempos em s, `atraso` <= 0 para a animacao ja nascer em andamento. */
export type Ponto = { x: number; y: number; tamanho: number; opacidade: number; pisca: boolean; ciclo: number; atraso: number };
export type Risco = { x: number; y: number; comprimento: number; alfa: number; duracao: number; atraso: number };

export const SEMENTE_CEU = 7;
const TOTAL_PONTOS = 140;
const TOTAL_RISCOS = 26;

/** PRNG mulberry32: pequena, rapida e reprodutivel. */
function mulberry32(semente: number): () => number {
  let a = semente >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const entre = (sorteio: () => number, minimo: number, maximo: number) => minimo + sorteio() * (maximo - minimo);
const arredondar = (valor: number, casas: number) => Number(valor.toFixed(casas));
const escolher = <T,>(sorteio: () => number, opcoes: readonly T[]) => opcoes[Math.floor(sorteio() * opcoes.length)];

export function gerarCeu(semente: number): { pontos: Ponto[]; riscos: Risco[] } {
  const sorteio = mulberry32(semente);
  const pontos: Ponto[] = [];
  for (let i = 0; i < TOTAL_PONTOS; i += 1) {
    const grande = sorteio() < 0.08;
    const tamanho = grande ? escolher(sorteio, [5, 6, 7] as const) : escolher(sorteio, [1.5, 2, 2.5, 3] as const);
    const pisca = sorteio() < 0.6;
    const ciclo = arredondar(entre(sorteio, 2.5, 7), 1);
    pontos.push({
      x: arredondar(entre(sorteio, 0, 100), 2),
      y: arredondar(entre(sorteio, 0, 100), 2),
      tamanho,
      opacidade: arredondar(entre(sorteio, 0.35, 1), 2),
      pisca,
      ciclo,
      atraso: 0 - arredondar(sorteio() * ciclo, 1),
    });
  }
  const riscos: Risco[] = [];
  for (let i = 0; i < TOTAL_RISCOS; i += 1) {
    const duracao = arredondar(entre(sorteio, 14, 30), 1);
    riscos.push({
      x: arredondar(entre(sorteio, -20, 110), 1),
      y: arredondar(entre(sorteio, -30, 100), 1),
      comprimento: Math.round(entre(sorteio, 180, 520)),
      alfa: arredondar(entre(sorteio, 0.04, 0.12), 2),
      duracao,
      atraso: 0 - arredondar(sorteio() * duracao, 1),
    });
  }
  return { pontos, riscos };
}
