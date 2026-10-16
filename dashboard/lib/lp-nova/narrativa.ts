export type Etapa = 0 | 1 | 2 | 3;
export type CaixaDaCena = { etapa: Etapa; top: number; bottom: number };

/** Mais area vertical visivel; empate favorece a cena mais perto do centro. */
export function escolherEtapa(cenas: CaixaDaCena[], altura: number): Etapa | null {
  let melhor: { etapa: Etapa; visivel: number; centro: number } | null = null;
  for (const cena of cenas) {
    const visivel = Math.max(0, Math.min(cena.bottom, altura) - Math.max(cena.top, 0));
    const centro = Math.abs((cena.top + cena.bottom) / 2 - altura / 2);
    if (visivel > 0 && (!melhor || visivel > melhor.visivel || (visivel === melhor.visivel && centro < melhor.centro))) {
      melhor = { etapa: cena.etapa, visivel, centro };
    }
  }
  return melhor?.etapa ?? null;
}

/** Observa o fluxo normal; nunca intercepta scroll nem acumula transicoes. */
export function acompanharNarrativa(raiz: HTMLElement, aoMudar: (etapa: Etapa) => void) {
  const cenas = [...raiz.querySelectorAll<HTMLElement>("[data-cena]")];
  let ativa: Etapa | null = null;
  const medir = () => {
    const proxima = escolherEtapa(cenas.map((cena) => {
      const { top, bottom } = cena.getBoundingClientRect();
      return { etapa: Number(cena.dataset.cena) as Etapa, top, bottom };
    }), window.innerHeight);
    if (proxima === null || proxima === ativa) return;
    ativa = proxima;
    aoMudar(proxima);
  };
  const observador = new IntersectionObserver(medir, {
    threshold: Array.from({ length: 101 }, (_, i) => i / 100),
  });
  cenas.forEach((cena) => observador.observe(cena));
  const layout = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(medir);
  layout?.observe(raiz);
  raiz.addEventListener("toggle", medir, true);
  window.addEventListener("resize", medir);
  medir();
  return () => {
    observador.disconnect();
    layout?.disconnect();
    raiz.removeEventListener("toggle", medir, true);
    window.removeEventListener("resize", medir);
  };
}
