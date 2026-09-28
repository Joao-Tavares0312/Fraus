"use client";

import { lazy, Suspense, useEffect, useRef, useState } from "react";

const CenaScroll3D = lazy(() => import("@/components/lp/CenaScroll3D").then((modulo) => ({ default: modulo.CenaScroll3D })));

function ReservaDaCena() {
  return <section aria-hidden className="h-[320svh] border-y border-linha bg-card/10" />;
}

export function CenaScroll3DPorta() {
  const porta = useRef<HTMLDivElement>(null);
  const [ativar, setAtivar] = useState(false);

  useEffect(() => {
    const elemento = porta.current;
    if (!elemento || ativar) return;
    const observador = new IntersectionObserver(([entrada]) => {
      if (!entrada.isIntersecting) return;
      setAtivar(true);
      observador.disconnect();
    }, { rootMargin: "1200px 0px" });
    observador.observe(elemento);
    return () => observador.disconnect();
  }, [ativar]);

  return (
    <div ref={porta}>
      {ativar ? <Suspense fallback={<ReservaDaCena />}><CenaScroll3D /></Suspense> : <ReservaDaCena />}
    </div>
  );
}
