/**
 * =============================================================================
 * O VOCABULARIO DE MOVIMENTO
 *
 * Um lugar so para duracao e curva, pelo mesmo motivo que a cor mora em token:
 * transicao digitada a mao em cada componente vira dez dialetos que ninguem
 * consegue afinar depois.
 *
 * A REGRA DA CASA (DESIGN.md, secao 6, emendada em 24/08): a janela e
 * 150-250ms e a curva e sempre `--ease-fluid`. Movimento aqui existe para
 * dizer de onde um elemento veio ou para onde um valor foi -- nunca para
 * anunciar que a pagina carregou.
 *
 * O QUE ESTE MODULO NAO FAZ: `prefers-reduced-motion`. O bloco no fim do
 * globals.css zera transicao CSS, mas nao alcanca animacao do Motion, que roda
 * em JS. Quem anima chama `useReducedMotion()` e escolhe o estado final direto.
 * Ver `useMovimento` abaixo.
 * =============================================================================
 */

import type { Transition, Variants } from "motion/react";

/**
 * A mesma curva do `--ease-fluid` do globals.css, em array porque o Motion
 * anima em JS e nao le variavel CSS. Se um dia mudar la, muda aqui -- sao a
 * mesma decisao escrita em duas linguagens.
 */
export const CURVA = [0.32, 0.72, 0, 1] as const;

/** A janela da secao 6. Nada nesta interface anima fora dela. */
export const DURACAO = {
  /** Reacao a toque: press, hover, chevron. */
  gesto: 0.15,
  /** O padrao. Entrada de sistema, troca de estado. */
  padrao: 0.2,
  /** Abertura de aparato, remanejo de layout -- o que percorre mais distancia. */
  amplo: 0.25,
} as const;

export const TRANSICAO: Record<keyof typeof DURACAO, Transition> = {
  gesto: { duration: DURACAO.gesto, ease: CURVA },
  padrao: { duration: DURACAO.padrao, ease: CURVA },
  amplo: { duration: DURACAO.amplo, ease: CURVA },
};

/**
 * A DISTANCIA da entrada. 8px: o bastante para o olho ler "veio de baixo", nao
 * o bastante para o texto parecer que escorregou. Deslocamento maior chama
 * atencao para o movimento em vez do dado.
 */
const SUBIDA = 8;

/**
 * O SISTEMA entrando. Usado por `Painel` e pela armadura de indicadores -- as
 * duas unidades de composicao da pagina (DESIGN.md, secao 2).
 */
export const entradaDeSistema: Variants = {
  oculto: { opacity: 0, y: SUBIDA },
  presente: { opacity: 1, y: 0, transition: TRANSICAO.padrao },
};

/**
 * A PILHA. Container que escalona os filhos.
 *
 * 40ms entre irmaos, e nao os 80-100ms de praxe: com quatro indicadores, 100ms
 * faz o ultimo chegar 400ms depois do primeiro, e o analista fica esperando a
 * armadura montar. 40ms le como um gesto unico com textura, nao como fila.
 */
export const pilha: Variants = {
  oculto: {},
  presente: { transition: { staggerChildren: 0.04 } },
};

/** O item da pilha. Par de `pilha`. */
export const itemDaPilha: Variants = entradaDeSistema;

/**
 * O APARATO abrindo. Anima altura, entao precisa de `overflow: hidden` em quem
 * envolve -- ver `Aparato`.
 */
export const aberturaDeAparato: Variants = {
  fechado: { height: 0, opacity: 0 },
  aberto: { height: "auto", opacity: 1 },
};

/**
 * O ESTADO TROCANDO no mesmo lugar: esqueleto -> dado, periodo antigo ->
 * periodo novo. So opacidade, sem deslocamento: o dado novo nasce onde o
 * antigo estava, porque o lugar na pagina e o mesmo e mover sugeriria que nao.
 */
export const trocaDeEstado: Variants = {
  saindo: { opacity: 0 },
  presente: { opacity: 1 },
};
