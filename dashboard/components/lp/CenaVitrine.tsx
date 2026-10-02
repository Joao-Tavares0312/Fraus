"use client";

import { useEffect, useRef } from "react";
import { iniciarMotor } from "@/lib/vitrine/motor";

/**
 * A CASCA DA CENA: o unico componente de cliente da vitrine.
 *
 * Monta o canvas fixo atras do conteudo e entrega a raiz ao motor
 * (`lib/vitrine/motor.ts`), que faz o resto imperativamente. As secoes sao
 * Server Components passados como `children`: o HTML chega pronto e legivel
 * antes de qualquer JavaScript, e o motor so acrescenta a coreografia
 * (`vt-vivo`) ou o regime parado (`vt-estatico`).
 */
export function CenaVitrine({ children }: { children: React.ReactNode }) {
  const raiz = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!raiz.current || !canvas.current) return;
    return iniciarMotor(raiz.current, canvas.current);
  }, []);

  return (
    <div ref={raiz} className="vt">
      <canvas ref={canvas} aria-hidden className="vt-cena" />
      <div aria-hidden className="vt-grao" />
      {children}
    </div>
  );
}
