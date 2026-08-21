"use client";

import { useEffect, useRef } from "react";

/**
 * O REALCE ESPECULAR: o brilho que acompanha o ponteiro sobre o vidro.
 *
 * Devolve uma ref para pendurar no elemento que tem a classe `.especular`. O
 * hook escreve `--px` e `--py` (a posicao do ponteiro dentro do elemento, em
 * porcentagem) DIRETO no `style` do no, dentro de um `requestAnimationFrame`.
 *
 * POR QUE NAO `useState`: um estado por `pointermove` repintaria a arvore
 * inteira da dashboard a cada movimento do mouse, com Recharts e o canvas do
 * grafo montados. O realce e puramente visual e nao pertence ao estado do
 * React -- escrever no no e a implementacao correta, nao um atalho.
 *
 * OS DOIS DESLIGAMENTOS, e o segundo e o que costuma ser esquecido:
 *   - `prefers-reduced-motion: reduce` -- o realce some, o vidro fica;
 *   - `pointer: coarse` -- toque nao tem hover, entao o realce congelaria no
 *     ultimo ponto tocado, o que e pior do que nao existir.
 * Ambos sao consultados aqui E no CSS: aqui para nao pendurar listener a toa,
 * no CSS para que o pseudo-elemento nao exista.
 */
export function useEspecular<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const no = ref.current;
    if (!no) return;

    const semMovimento = window.matchMedia("(prefers-reduced-motion: reduce)");
    const ponteiroGrosso = window.matchMedia("(pointer: coarse)");
    if (semMovimento.matches || ponteiroGrosso.matches) return;

    let quadro = 0;

    function aoMover(evento: PointerEvent) {
      if (quadro) return;
      quadro = requestAnimationFrame(() => {
        quadro = 0;
        const alvo = ref.current;
        if (!alvo) return;
        const caixa = alvo.getBoundingClientRect();
        if (caixa.width === 0 || caixa.height === 0) return;
        const x = ((evento.clientX - caixa.left) / caixa.width) * 100;
        const y = ((evento.clientY - caixa.top) / caixa.height) * 100;
        alvo.style.setProperty("--px", `${x.toFixed(2)}%`);
        alvo.style.setProperty("--py", `${y.toFixed(2)}%`);
      });
    }

    function aoSair() {
      const alvo = ref.current;
      if (!alvo) return;
      // Volta ao repouso em vez de congelar o brilho na ultima posicao: vidro
      // parado com um realce aceso fora do ponteiro parece defeito.
      alvo.style.removeProperty("--px");
      alvo.style.removeProperty("--py");
    }

    no.addEventListener("pointermove", aoMover);
    no.addEventListener("pointerleave", aoSair);
    return () => {
      if (quadro) cancelAnimationFrame(quadro);
      no.removeEventListener("pointermove", aoMover);
      no.removeEventListener("pointerleave", aoSair);
    };
  }, []);

  return ref;
}
