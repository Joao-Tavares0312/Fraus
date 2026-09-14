"use client";

import { useSyncExternalStore } from "react";

const LARGURA_MOBILE = 768;
const CONSULTA = `(max-width: ${LARGURA_MOBILE - 1}px)`;

function assinar(aoMudar: () => void): () => void {
  const consulta = window.matchMedia(CONSULTA);
  consulta.addEventListener("change", aoMudar);
  return () => consulta.removeEventListener("change", aoMudar);
}

function lerNavegador(): boolean {
  return window.matchMedia(CONSULTA).matches;
}

/** O servidor nao sabe a largura da janela: o desktop e o palpite. */
function lerServidor(): boolean {
  return false;
}

/**
 * Hook padrao do chassi shadcn, exigido por `components/ui/sidebar.tsx` para
 * decidir entre a barra fixa e a gaveta.
 *
 * `useSyncExternalStore`, e nao `useState(false)` + efeito, e a diferenca so
 * aparece no celular: a `NavegacaoLateral` mora dentro de um `<Suspense>`
 * (`app/dashboard/layout.tsx`), e conteudo de Suspense e hidratado DEPOIS dos
 * efeitos do pai. Com o estado em efeito, quando a barra ia hidratar o
 * `SidebarProvider` ja tinha trocado para `true`, e ela tentava virar gaveta
 * em cima do HTML de barra fixa -- erro de hidratacao em toda tela da
 * dashboard abaixo de 768px, com a arvore inteira regerada no cliente
 * (medido em 14/09/2026 a 390px; a 1280px nao acontecia). Aqui, qualquer
 * render de hidratacao usa `lerServidor`, e so depois o valor do navegador.
 */
export function useIsMobile() {
  return useSyncExternalStore(assinar, lerNavegador, lerServidor);
}
