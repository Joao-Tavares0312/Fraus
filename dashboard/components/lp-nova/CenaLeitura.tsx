"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { iniciarCena, type CenaLeitura as Cena } from "@/lib/lp-nova/cena";
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

export function CenaLeitura({ children }: { children: React.ReactNode }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const cena = useRef<Cena | null>(null);
  const [estado, setEstado] = useState<EstadoRegime | null>(null);

  useEffect(() => {
    if (!canvas.current) return;
    const elementoFrase = document.querySelector<HTMLElement>("[data-ln='frase']");
    const frase = elementoFrase
      ? {
          texto: elementoFrase.textContent ?? "",
          caixa: elementoFrase.getBoundingClientRect(),
          fonte: getComputedStyle(elementoFrase).font,
        }
      : null;
    const nova = iniciarCena(canvas.current, {
      celular: window.matchMedia("(max-width: 899px)").matches,
      movimentoReduzido: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
      frase,
      aoMudarRegime: setEstado,
    });
    cena.current = nova;

    const medir = () => {
      const maximo = document.documentElement.scrollHeight - window.innerHeight;
      nova.definirProgresso(maximo > 0 ? window.scrollY / maximo : 0);
    };
    medir();
    window.addEventListener("scroll", medir, { passive: true });
    window.addEventListener("resize", medir);
    return () => {
      window.removeEventListener("scroll", medir);
      window.removeEventListener("resize", medir);
      nova.dispose();
      cena.current = null;
    };
  }, []);

  const regime = estado?.regime;
  return (
    <ContextoCena.Provider
      value={{ definirHumor: (h, c) => cena.current?.definirHumor(h, c) }}
    >
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
