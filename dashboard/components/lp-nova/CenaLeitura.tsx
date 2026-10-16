"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import type { ReactNode } from "react";
import { RotateCcw } from "lucide-react";
import { ArteEstatica } from "./ArteEstatica";
import { acompanharNarrativa } from "@/lib/lp-nova/narrativa";
import type { Etapa } from "@/lib/lp-nova/narrativa";
import type { EsculturaFraus as TipoEsculturaFraus } from "./EsculturaFraus";

const CONSULTA_ARTE = "(min-width: 900px) and (prefers-reduced-motion: no-preference)";
function observarArte(avisar: () => void) {
  const consulta = window.matchMedia(CONSULTA_ARTE);
  consulta.addEventListener("change", avisar);
  return () => consulta.removeEventListener("change", avisar);
}
function arteInterativa() { return window.matchMedia(CONSULTA_ARTE).matches; }
function arteNoServidor() { return false; }

/** Texto SSR em fluxo normal; apenas a arte sticky responde a etapa visivel. */
export function CenaLeitura({ children }: { children: ReactNode }) {
  const raiz = useRef<HTMLDivElement>(null);
  const [etapa, setEtapa] = useState<Etapa>(0);
  const [repeticao, setRepeticao] = useState(0);
  const [disponivel, setDisponivel] = useState(false);
  const interativa = useSyncExternalStore(observarArte, arteInterativa, arteNoServidor);
  const [Escultura, setEscultura] = useState<typeof TipoEsculturaFraus | null>(null);

  useEffect(() => {
    if (!interativa || Escultura) return;
    let saiu = false;
    void import("./EsculturaFraus").then(
      (modulo) => { if (!saiu) setEscultura(() => modulo.EsculturaFraus); },
      (erro) => console.error("Não foi possível carregar a arte interativa do Fraus.", erro),
    );
    return () => { saiu = true; };
  }, [interativa, Escultura]);

  useEffect(() => {
    if (!interativa || !raiz.current) return;
    return acompanharNarrativa(raiz.current, setEtapa);
  }, [interativa]);

  return (
    <div className="narrativa" ref={raiz} data-etapa={etapa}>
      <div className="textos">{children}</div>
      <aside className="palco" aria-label="Arte da marca Fraus">
        <div className="objeto-desktop" aria-hidden="true">
          {interativa && Escultura
            ? <Escultura etapa={etapa} repeticao={repeticao} aoDisponibilizar={setDisponivel} />
            : <ArteEstatica etapa={etapa} />}
        </div>
        <div className="legenda-arte">
          <span>Contexto, não certeza.</span>
          {interativa && Escultura && disponivel && <button type="button" onClick={() => setRepeticao((valor) => valor + 1)}><RotateCcw className="icone-lp" aria-hidden="true" />Rever esta etapa</button>}
        </div>
      </aside>
    </div>
  );
}
