"use client";

import { useEffect, useRef } from "react";
import type { Etapa } from "@/lib/lp-nova/narrativa";
import { criarRenderizadorFR } from "@/lib/lp-nova/renderizador-fr";
import type { RenderizadorFR } from "@/lib/lp-nova/renderizador-fr";
import { ArteEstatica } from "./ArteEstatica";

/** Um unico canvas vivo; o FR raster permanece ate existir um quadro valido. */
export function EsculturaFraus({ etapa, repeticao, aoDisponibilizar }: {
  etapa: Etapa;
  repeticao: number;
  aoDisponibilizar: (disponivel: boolean) => void;
}) {
  const raiz = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const renderizador = useRef<RenderizadorFR | null>(null);
  const ultima = useRef({ etapa, repeticao });

  useEffect(() => {
    const elemento = canvas.current;
    const caixa = raiz.current;
    if (!elemento || !caixa) return;
    const iniciar = () => {
      renderizador.current?.destruir();
      renderizador.current = null;
      caixa.dataset.frEstado = "estatico";
      caixa.dataset.frMovimento = "parado";
      aoDisponibilizar(false);
      try {
        renderizador.current = criarRenderizadorFR(elemento, ultima.current.etapa, (animando) => {
          caixa.dataset.frMovimento = animando ? "animando" : "parado";
          if (!animando) caixa.dataset.frAssentada = String(ultima.current.etapa);
        });
        caixa.dataset.frEstado = "pronto";
        caixa.dataset.frAssentada = String(ultima.current.etapa);
        caixa.dataset.frBackend = elemento.dataset.frBackend ?? "contexto";
        aoDisponibilizar(true);
      } catch {
        // A marca pre-renderizada e uma alternativa real, nao um canvas vazio.
        caixa.dataset.frEstado = "estatico";
        caixa.dataset.frBackend = elemento.dataset.frBackend ?? "erro";
      }
    };
    const perder = (evento: Event) => {
      evento.preventDefault();
      renderizador.current?.destruir();
      renderizador.current = null;
      caixa.dataset.frEstado = "estatico";
      caixa.dataset.frMovimento = "parado";
      aoDisponibilizar(false);
    };
    elemento.addEventListener("webglcontextlost", perder);
    elemento.addEventListener("webglcontextrestored", iniciar);
    iniciar();
    return () => {
      elemento.removeEventListener("webglcontextlost", perder);
      elemento.removeEventListener("webglcontextrestored", iniciar);
      renderizador.current?.destruir();
      renderizador.current = null;
      aoDisponibilizar(false);
    };
  }, [aoDisponibilizar]);

  useEffect(() => {
    const anterior = ultima.current;
    ultima.current = { etapa, repeticao };
    if (anterior.etapa !== etapa || anterior.repeticao !== repeticao) {
      renderizador.current?.irPara(etapa, anterior.repeticao !== repeticao);
    }
  }, [etapa, repeticao]);

  return (
    <div ref={raiz} className="fr-renderizador" aria-hidden="true" data-fr-etapa={etapa}>
      <ArteEstatica etapa={etapa} />
      <div className="fr-sombra" />
      <canvas ref={canvas} className="fr-canvas" />
    </div>
  );
}
