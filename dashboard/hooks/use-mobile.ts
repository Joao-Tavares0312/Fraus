import * as React from "react"

const MOBILE_BREAKPOINT = 768
const CONSULTA = `(max-width: ${MOBILE_BREAKPOINT - 1}px)`

/**
 * Versao do hook do shadcn escrita com `useSyncExternalStore`.
 *
 * O original faz `setState` sincrono dentro de um `useEffect`, o que dispara
 * render em cascata e e erro no lint deste projeto. `useSyncExternalStore` e a
 * forma correta de ler um `matchMedia`: ele tem snapshot proprio para o
 * servidor (sempre `false`, porque nao ha viewport na renderizacao) e assina o
 * evento `change` sem passar por estado do React.
 */
function assinar(aoMudar: () => void) {
  const mql = window.matchMedia(CONSULTA)
  mql.addEventListener("change", aoMudar)
  return () => mql.removeEventListener("change", aoMudar)
}

function lerNoCliente() {
  return window.matchMedia(CONSULTA).matches
}

function lerNoServidor() {
  return false
}

export function useIsMobile() {
  return React.useSyncExternalStore(assinar, lerNoCliente, lerNoServidor)
}
