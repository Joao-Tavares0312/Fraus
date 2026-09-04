/**
 * A CENA DA VITRINE: como cada camada do atelie responde a rolagem.
 *
 * O DEFEITO QUE ISTO CONSERTA: o atelie so existia no heroi. Grade, planeta e
 * campo de estrelas ocupavam a primeira tela e a LP virava preto chapado por
 * cerca de 5.600px -- a tese "espaco profundo" evaporava exatamente onde a
 * rolagem passa o tempo todo.
 *
 * O QUE ESTA FUNCAO DEVOLVE: um FATOR de 0 a 1, nao uma opacidade. As
 * camadas reais sao tokens por tema (`--grade-op`, `--sol-op`, `--estrelas-op`
 * em `app/globals.css`), porque cada tema decide a propria intensidade --
 * inclusive o zero deliberado de `--estrelas-op` na chuva de neon, onde o
 * globals.css registra, em comentario, que nao ha estrela visivel sob chuva
 * e poluicao luminosa. Um teto absoluto aqui atropelaria essa decisao: um
 * fator maximo travado em opacidade acenderia estrelas num tema que decidiu
 * nao ter nenhuma. A conta certa e do consumidor: `opacidade final = fator x
 * token do tema` -- fator vezes o zero da chuva continua zero, por
 * construcao, sem essa funcao precisar saber que a chuva existe.
 *
 * POR QUE FUNCAO PURA, e nao numeros soltos no componente: o FATOR MAXIMO de
 * cada camada e o que o `scripts/pisos.mjs` precisa multiplicar pelo token de
 * cada tema para saber a superficie mais clara que o vidro pode compor, tema
 * a tema. Fator escondido dentro de JSX e fator que o script nao le -- e o
 * portao passa a medir uma superficie que nao existe, que a §8.6 do
 * DESIGN.md registra ter acontecido duas vezes aqui.
 *
 * O QUE NAO MUDA: estas camadas moram no ATELIE, nao carregam dado, e passam
 * por baixo da luz e do vidro.
 */

export type Camada = "grade" | "planeta" | "estrelas";

/**
 * Fator maximo (0..1) que cada camada assume em QUALQUER ponto da rolagem.
 * NAO e opacidade -- quem escala pelo token de opacidade do tema vigente e o
 * consumidor. Espelhado em `scripts/pisos.mjs`; mudar aqui obriga a remedir
 * la, tema a tema.
 */
export const FATOR_MAXIMO_POR_CAMADA: Record<Camada, number> = {
  grade: 1,
  planeta: 1,
  estrelas: 1,
};

function limitar(valor: number, minimo: number, maximo: number): number {
  // Number.isNaN primeiro: Math.max/Math.min propagam NaN em vez de
  // grampear, e NaN e o que scrollY / rolavel produz quando a pagina e curta
  // demais para rolar (rolavel = 0) ou quando o layout ainda nao mediu. O
  // extremo seguro e o minimo -- cena apagada, nunca clara demais.
  if (Number.isNaN(valor)) {
    return minimo;
  }
  return Math.min(maximo, Math.max(minimo, valor));
}

/**
 * `progresso` e 0 no topo da pagina e 1 no fim. Valores fora da faixa sao
 * grampeados: `scroll` elastico de trackpad entrega negativo e passa de 1, e
 * uma camada com fator negativo e um NaN esperando acontecer.
 *
 * `NaN` e tratado ANTES do grampeamento de `progresso`, nao depois: grampear
 * para p=0 nao basta, porque a grade e mais forte exatamente em p=0 (o
 * heroi). Se so o `progresso` fosse grampeado, `NaN` acenderia a grade no
 * maximo em vez de apaga-la. `NaN` e o que `scrollY / rolavel` produz quando
 * a pagina e curta demais para rolar (`rolavel = 0`) ou antes do layout
 * medir -- o extremo seguro para QUALQUER camada nesse caso e 0, cena
 * apagada, nunca clara demais.
 */
export function intensidadeDaCamada(camada: Camada, progresso: number): number {
  if (Number.isNaN(progresso)) {
    return 0;
  }

  const p = limitar(progresso, 0, 1);
  const teto = FATOR_MAXIMO_POR_CAMADA[camada];

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
