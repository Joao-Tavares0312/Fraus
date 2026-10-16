"use client";

import { MotionConfig } from "motion/react";
import type { ReactNode } from "react";

/**
 * A CHAVE GERAL do movimento.
 *
 * Existe por um motivo unico e importante: o bloco `prefers-reduced-motion` no
 * fim do globals.css zera `transition-duration` de tudo, mas ele NAO alcanca o
 * Motion, que anima em JS escrevendo `style` quadro a quadro -- um `!important`
 * de CSS nao para um loop de rAF. Sem esta camada, quem pediu menos movimento
 * ao sistema operacional continuaria recebendo todo o movimento desta pagina.
 *
 * `reducedMotion="user"` faz o Motion ler a mesma media query e descartar
 * transform, layout e escala, preservando so opacidade -- a leitura correta da
 * preferencia, que pede menos DESLOCAMENTO, nao ausencia total de feedback.
 *
 * Envolve a dashboard, onde o Motion e usado. A LP usa CSS e media query
 * nativa; carregar esta biblioteca nela acrescentaria JavaScript sem uso.
 */
export function Movimento({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
