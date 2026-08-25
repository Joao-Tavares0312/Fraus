/**
 * A MAQUINA DO SEGREDO.
 *
 * Cinco cliques na marca dentro da janela abrem a fenda. Funcao PURA, sem React
 * e sem relogio proprio: quem chama passa o instante. E o que torna a janela de
 * tempo testavel sem esperar de verdade -- teste que dorme 2s e teste que
 * ninguem roda.
 *
 * O estado vive so na memoria de quem chama. Nada de localStorage, banco ou URL:
 * segredo que persiste vira configuracao, e configuracao tem painel.
 */

/** Silencio acima disto zera a contagem. */
export const JANELA_MS = 2_000;

/** Quantos cliques abrem a fenda. */
export const CLIQUES_PARA_ABRIR = 5;

export type EstadoContador = {
  /** Quantos cliques validos ate agora. */
  readonly cliques: number;
  /** O instante do ultimo, em ms. */
  readonly ultimoEm: number;
};

export const CONTADOR_ZERADO: EstadoContador = { cliques: 0, ultimoEm: 0 };

/**
 * Registra um clique em `agoraMs` e devolve o estado novo.
 *
 * A janela e medida contra o ULTIMO clique, nao contra o primeiro: cinco cliques
 * calmos, um a cada 1,5s, sao uma sequencia deliberada e tem que valer. Medir
 * contra o primeiro exigiria pressa, e pressa nao e o que distingue quem
 * descobriu o segredo de quem clicou por acaso.
 *
 * Ja tendo aberto, o proximo clique recomeca do um -- senao a fenda reabriria a
 * cada clique subsequente.
 */
export function registrarClique(
  estado: EstadoContador,
  agoraMs: number,
): EstadoContador {
  const expirou = agoraMs - estado.ultimoEm > JANELA_MS;
  const recomeca = expirou || abriu(estado);
  return {
    cliques: recomeca ? 1 : estado.cliques + 1,
    ultimoEm: agoraMs,
  };
}

/** A fenda abre exatamente no quinto. */
export function abriu(estado: EstadoContador): boolean {
  return estado.cliques >= CLIQUES_PARA_ABRIR;
}
