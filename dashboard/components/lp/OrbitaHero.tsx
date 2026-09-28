"use client";

import { motion, useScroll, useTransform } from "motion/react";
import { useRef, type PointerEvent } from "react";

export function OrbitaHero() {
  const cena = useRef<HTMLDivElement>(null);
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 900], [0, 150]);
  const escala = useTransform(scrollY, [0, 900], [1, 0.78]);
  const opacidade = useTransform(scrollY, [0, 720], [1, 0.16]);

  function inclinar(evento: PointerEvent<HTMLDivElement>) {
    const elemento = cena.current;
    if (!elemento) return;
    const caixa = elemento.getBoundingClientRect();
    const x = (evento.clientX - caixa.left) / caixa.width - 0.5;
    const yLocal = (evento.clientY - caixa.top) / caixa.height - 0.5;
    elemento.style.setProperty("--orbita-rx", `${-yLocal * 7}deg`);
    elemento.style.setProperty("--orbita-ry", `${x * 9}deg`);
    elemento.style.setProperty("--orbita-x", `${x * 10}px`);
    elemento.style.setProperty("--orbita-y", `${yLocal * 8}px`);
  }

  function repousar() {
    const elemento = cena.current;
    if (!elemento) return;
    elemento.style.setProperty("--orbita-rx", "0deg");
    elemento.style.setProperty("--orbita-ry", "0deg");
    elemento.style.setProperty("--orbita-x", "0px");
    elemento.style.setProperty("--orbita-y", "0px");
  }

  return (
    <motion.div style={{ y, scale: escala, opacity: opacidade }} className="sistema-fraus-cena">
      <div ref={cena} onPointerMove={inclinar} onPointerLeave={repousar} aria-hidden className="sistema-fraus relative mx-auto aspect-square w-full max-w-[38rem]">
        <div className="sistema-fraus__lente absolute inset-[1%] rounded-full" />
        <div className="sistema-fraus__orbita sistema-fraus__orbita--externa"><i /></div>
        <div className="sistema-fraus__orbita sistema-fraus__orbita--media"><i /></div>
        <div className="sistema-fraus__orbita sistema-fraus__orbita--interna"><i /></div>
        <div className="sistema-fraus__nucleo absolute left-1/2 top-1/2 size-[26%] -translate-x-1/2 -translate-y-1/2 rounded-full">
          <span className="sistema-fraus__superficie absolute inset-0 overflow-hidden rounded-full"><i /></span>
          <span className="sistema-fraus__atmosfera absolute rounded-full" />
        </div>
        <div className="absolute left-[48%] top-[2%] font-mono text-[.6875rem] uppercase tracking-[.2em] text-muted-foreground">frs / sistema 07</div>
        <div className="absolute bottom-[7%] right-0 text-right font-mono text-[.6875rem] uppercase leading-5 tracking-[.16em] text-muted-foreground">telemetria ativa<br />sete sinais · um score</div>
        <div className="absolute bottom-[18%] left-[3%] font-mono text-[.6875rem] uppercase leading-5 tracking-[.16em] text-muted-foreground">lat −23.55<br />long −46.63</div>
        <div className="sistema-fraus__leitura absolute right-[4%] top-[22%] font-mono text-[.6875rem] uppercase leading-5 tracking-[.14em] text-medido-texto"><span>confiança</span><b>0.92</b></div>
      </div>
    </motion.div>
  );
}
