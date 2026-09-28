"use client";

import { lazy, Suspense, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { CenaScrollLeve } from "@/components/lp/CenaScrollLeve";
import { permiteCena3D } from "@/lib/capacidade-visual";

const CenaScroll3D = lazy(() => import("@/components/lp/CenaScroll3D").then((modulo) => ({ default: modulo.CenaScroll3D })));

function ReservaDaCena() {
  return <section aria-hidden className="h-[320svh] border-y border-linha bg-card/10" />;
}

const CONSULTA_MOVIMENTO = "(prefers-reduced-motion: reduce)";

function assinarCapacidade(aoMudar: () => void) {
  const movimento = window.matchMedia(CONSULTA_MOVIMENTO);
  const conexao = (navigator as Navigator & { connection?: EventTarget }).connection;
  movimento.addEventListener("change", aoMudar);
  window.addEventListener("resize", aoMudar);
  conexao?.addEventListener("change", aoMudar);
  return () => {
    movimento.removeEventListener("change", aoMudar);
    window.removeEventListener("resize", aoMudar);
    conexao?.removeEventListener("change", aoMudar);
  };
}

function lerCapacidade() {
  const navegador = navigator as Navigator & {
    connection?: { saveData?: boolean };
    deviceMemory?: number;
  };
  return permiteCena3D({
    largura: window.innerWidth,
    movimentoReduzido: window.matchMedia(CONSULTA_MOVIMENTO).matches,
    economizarDados: navegador.connection?.saveData === true,
    memoriaGb: navegador.deviceMemory,
    nucleos: navegador.hardwareConcurrency,
  });
}

export function CenaScroll3DPorta() {
  const porta = useRef<HTMLDivElement>(null);
  const [ativar, setAtivar] = useState(false);
  const usar3D = useSyncExternalStore(assinarCapacidade, lerCapacidade, () => false);

  useEffect(() => {
    const elemento = porta.current;
    if (!elemento || ativar || usar3D !== true) return;
    const observador = new IntersectionObserver(([entrada]) => {
      if (!entrada.isIntersecting) return;
      setAtivar(true);
      observador.disconnect();
    }, { rootMargin: "400px 0px" });
    observador.observe(elemento);
    return () => observador.disconnect();
  }, [ativar, usar3D]);

  return (
    <div ref={porta}>
      {!usar3D ? <CenaScrollLeve /> : ativar ? <Suspense fallback={<ReservaDaCena />}><CenaScroll3D /></Suspense> : <ReservaDaCena />}
    </div>
  );
}
