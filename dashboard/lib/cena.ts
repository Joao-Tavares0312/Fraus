/**
 * A CENA DA VITRINE: como cada camada do atelie responde a rolagem.
 *
 * O DEFEITO QUE ISTO CONSERTA: o atelie so existia no heroi. Grade, planeta e
 * campo de estrelas ocupavam a primeira tela e a LP virava preto chapado por
 * cerca de 5.600px -- a tese "espaco profundo" evaporava exatamente onde a
 * rolagem passa o tempo todo.
 *
 * POR QUE FUNCAO PURA, e nao numeros soltos no componente: o TETO de cada
 * camada e o que o `scripts/pisos.mjs` mede para saber a superficie mais clara
 * que o vidro pode compor. Teto escondido dentro de JSX e teto que o script
 * nao le -- e o portao passa a medir uma superficie que nao existe, que a
 * §8.6 do DESIGN.md registra ter acontecido duas vezes aqui.
 *
 * O QUE NAO MUDA: estas camadas moram no ATELIE, nao carregam dado, e passam
 * por baixo da luz e do vidro.
 */

export type Camada = "grade" | "planeta" | "estrelas";

/**
 * Opacidade maxima que cada camada assume em QUALQUER ponto da rolagem.
 * Espelhado em `scripts/pisos.mjs`; mudar aqui obriga a remedir la.
 */
export const TETO_POR_CAMADA: Record<Camada, number> = {
  grade: 0.1,
  planeta: 0.15,
  estrelas: 0.22,
};

function limitar(valor: number, minimo: number, maximo: number): number {
  return Math.min(maximo, Math.max(minimo, valor));
}

/**
 * `progresso` e 0 no topo da pagina e 1 no fim. Valores fora da faixa sao
 * grampeados: `scroll` elastico de trackpad entrega negativo e passa de 1, e
 * uma camada com opacidade negativa e um NaN esperando acontecer.
 */
export function intensidadeDaCamada(camada: Camada, progresso: number): number {
  const p = limitar(progresso, 0, 1);
  const teto = TETO_POR_CAMADA[camada];

  switch (camada) {
    // A grade e o piso do cenario: forte na entrada, cede conforme a leitura
    // comeca, e nao volta.
    case "grade":
      return teto * (1 - p);
    // O planeta cruza: nasce fora, atinge o proprio teto no meio da travessia
    // e sai. Meia onda de seno, que garante o teto exatamente uma vez.
    case "planeta":
      return teto * Math.sin(Math.PI * p);
    // O campo de estrelas e o oposto da grade: quase ausente no heroi, onde a
    // manchete manda, e assume o fundo conforme a pagina desce.
    case "estrelas":
      return teto * p;
  }
}
