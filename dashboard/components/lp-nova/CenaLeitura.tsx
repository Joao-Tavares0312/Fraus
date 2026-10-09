"use client";

import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { iniciarCena, type CenaLeitura as Cena } from "@/lib/lp-nova/cena";
import { MARCOS, progressoDaRolagem, type Ancora } from "@/lib/lp-nova/fases";
import { rotuloDoRegime, type EstadoRegime } from "@/lib/lp-nova/regime";

/**
 * A CASCA DA CENA da LP nova: o unico componente de cliente com canvas.
 *
 * Mede o progresso da rolagem (0 no topo, 1 no fim) e entrega a cena; as
 * secoes sao Server Components passados como `children`, legiveis antes de
 * qualquer JavaScript. O rotulo do regime fica sempre visivel: estado vazio
 * nomeia o que falta, e uma cena parada sem explicacao parece pagina quebrada.
 */
const ContextoCena = createContext<{ definirHumor(humor: number, cinza: number): void }>({
  definirHumor() {},
});

export function useCena() {
  return useContext(ContextoCena);
}

function montar(
alvoCanvas: HTMLCanvasElement,
cena: { current: Cena | null },
aoMudarRegime: (estado: EstadoRegime) => void,
): () => void {
  const elementoFrase = document.querySelector<HTMLElement>("[data-ln='frase']");
  const frase = elementoFrase
    ? {
        texto: elementoFrase.textContent ?? "",
        caixa: elementoFrase.getBoundingClientRect(),
        // O atalho `font` volta vazio no Chrome; o canvas cairia em 10px.
        fonte: (() => {
          const e = getComputedStyle(elementoFrase);
          return `${e.fontWeight} ${e.fontSize} ${e.fontFamily}`;
        })(),
      }
    : null;
  const nova = iniciarCena(alvoCanvas, {
    celular: window.matchMedia("(max-width: 899px)").matches,
    movimentoReduzido: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    frase,
    aoMudarRegime,
  });
  cena.current = nova;

  // Cada secao marca ONDE o seu momento acontece; o fecho e o fim da rolagem.
  let ancoras: Ancora[] = [];
  const ancorar = () => {
    const meio = window.innerHeight * 0.5;
    ancoras = [...document.querySelectorAll<HTMLElement>("[data-marco]")].flatMap((el) => {
      const marco = el.dataset.marco as keyof typeof MARCOS;
      if (!(marco in MARCOS)) return [];
      const y =
        marco === "fecho"
          ? document.documentElement.scrollHeight - window.innerHeight
          : Math.max(0, el.getBoundingClientRect().top + window.scrollY - meio);
      return [{ y: marco === "frase" ? 0 : y, p: MARCOS[marco] }];
    });
  };
  const medir = () => nova.definirProgresso(progressoDaRolagem(window.scrollY, ancoras));
  const redimensionar = () => {
    ancorar();
    medir();
  };
  ancorar();
  medir();
  window.addEventListener("scroll", medir, { passive: true });
  window.addEventListener("resize", redimensionar);
  return () => {
    window.removeEventListener("scroll", medir);
    window.removeEventListener("resize", redimensionar);
    nova.dispose();
    cena.current = null;
  };
}

export function CenaLeitura({ children }: { children: React.ReactNode }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const cena = useRef<Cena | null>(null);
  const [estado, setEstado] = useState<EstadoRegime | null>(null);

  useEffect(() => {
    if (!canvas.current) return;
    const alvo = canvas.current;
    let desmontado = false;
    let soltar = () => {};
    // A frase so pode ser rasterizada com a fonte carregada: antes disso o
    // canvas 2D mede a fonte reserva e as particulas nao caem nos glifos.
    void document.fonts.ready.then(() => {
      if (desmontado) return;
      soltar = montar(alvo, cena, setEstado);
    });
    return () => {
      desmontado = true;
      soltar();
    };
  }, []);

  const regime = estado?.regime;
  // Estavel entre renders: o seletor o usa como dependencia de efeito.
  const contexto = useMemo(
    () => ({ definirHumor: (h: number, c: number) => cena.current?.definirHumor(h, c) }),
    [],
  );
  return (
    <ContextoCena.Provider value={contexto}>
      <div className="ln" data-regime={regime ?? "carregando"}>
        <canvas ref={canvas} aria-hidden className="ln-cena" />
        {children}
        {estado && (
          <p className="ln-regime" aria-live="polite">
            {rotuloDoRegime(estado.regime, estado.motivo)}
          </p>
        )}
      </div>
    </ContextoCena.Provider>
  );
}
