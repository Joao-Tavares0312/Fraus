"use client";

import { useEffect, useRef } from "react";
import fumaca from "@/lib/lp-nova/shaders/fumaca.wgsl";

/** Fumaca da Task 1: prova que o loader WGSL e o vgpu sobem no Next. Sai na Task 6. */
export function Fumaca() {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    let gpu: { dispose(): void } | undefined;
    let vivo = true;
    void (async () => {
      const { init, surface, effect, frame } = await import("vgpu");
      const g = await init();
      if (!vivo || !canvas.current) return g.dispose();
      gpu = g;
      const alvo = surface(g, canvas.current);
      const gradiente = effect(g, fumaca);
      frame(g, (f) => f.pass(alvo, gradiente));
    })();
    return () => {
      vivo = false;
      gpu?.dispose();
    };
  }, []);
  return <canvas ref={canvas} style={{ width: "100vw", height: "100vh", display: "block" }} />;
}
