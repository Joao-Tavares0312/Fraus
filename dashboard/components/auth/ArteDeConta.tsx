"use client";

import { useEffect, useRef } from "react";

/** A luz acontece uma vez; qualquer interrupção devolve a cena ao pôster. */
export function ArteDeConta() {
  const cenaRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const cena = cenaRef.current;
    const video = videoRef.current;
    const atelier = cena?.closest<HTMLElement>(".conta-atelier");
    const acesso = atelier?.parentElement?.querySelector<HTMLElement>(".conta-acesso");
    if (!cena || !video || !atelier || !acesso) return;

    const movimentoReduzido = window.matchMedia("(prefers-reduced-motion: reduce)");
    const ponteiroPreciso = window.matchMedia("(min-width: 900px) and (hover: hover) and (pointer: fine)");
    let encerrada = movimentoReduzido.matches || document.hidden || acesso.contains(document.activeElement);
    let desmontada = false;
    let iniciada = false;
    let emVista = false;
    let quadro: number | null = null;
    let deslocamentoX = 0;
    let deslocamentoY = 0;

    const zerarDeslocamento = () => {
      if (quadro !== null) cancelAnimationFrame(quadro);
      quadro = null;
      cena.style.removeProperty("--conta-deslocamento-x");
      cena.style.removeProperty("--conta-deslocamento-y");
    };
    const encerrarSequencia = () => {
      encerrada = true;
      video.hidden = true;
      if (video.hasAttribute("src")) {
        video.pause();
        video.removeAttribute("src");
        video.load();
      }
    };
    const interromper = () => {
      encerrarSequencia();
      zerarDeslocamento();
    };
    const podeAnimar = () => !movimentoReduzido.matches && !document.hidden && !acesso.contains(document.activeElement) && emVista;
    const iniciarSequencia = () => {
      if (encerrada || iniciada || !podeAnimar()) return;
      iniciada = true;
      // Sem src no HTML: quem reduz movimento não inicia nem o download.
      video.src = "/conta/fr-luz-de-corte.webm";
      void video.play().catch(() => {
        if (!desmontada) encerrarSequencia();
      });
    };
    const mostrarVideo = () => {
      if (encerrada || !podeAnimar()) {
        encerrarSequencia();
        return;
      }
      video.hidden = false;
    };
    const aoMudarMovimento = () => {
      if (movimentoReduzido.matches) interromper();
    };
    const aoMudarPonteiro = () => {
      if (!ponteiroPreciso.matches) zerarDeslocamento();
    };
    const aoMudarVisibilidade = () => {
      if (document.hidden) interromper();
    };
    const aoMoverPonteiro = (evento: PointerEvent) => {
      if (evento.pointerType !== "mouse" || !ponteiroPreciso.matches || !podeAnimar()) {
        zerarDeslocamento();
        return;
      }
      const limites = atelier.getBoundingClientRect();
      deslocamentoX = Math.max(-1, Math.min(1, ((evento.clientX - limites.left) / limites.width) * 2 - 1)) * 3;
      deslocamentoY = Math.max(-1, Math.min(1, ((evento.clientY - limites.top) / limites.height) * 2 - 1)) * 2;
      if (quadro !== null) return;
      quadro = requestAnimationFrame(() => {
        quadro = null;
        cena.style.setProperty("--conta-deslocamento-x", `${deslocamentoX}px`);
        cena.style.setProperty("--conta-deslocamento-y", `${deslocamentoY}px`);
      });
    };

    video.addEventListener("playing", mostrarVideo);
    video.addEventListener("ended", encerrarSequencia);
    video.addEventListener("error", encerrarSequencia);
    movimentoReduzido.addEventListener("change", aoMudarMovimento);
    ponteiroPreciso.addEventListener("change", aoMudarPonteiro);
    document.addEventListener("visibilitychange", aoMudarVisibilidade);
    acesso.addEventListener("focusin", interromper);
    atelier.addEventListener("pointermove", aoMoverPonteiro, { passive: true });
    atelier.addEventListener("pointerleave", zerarDeslocamento);
    atelier.addEventListener("pointercancel", zerarDeslocamento);

    const observador = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(([entrada]) => {
      emVista = entrada.isIntersecting;
      if (emVista) iniciarSequencia();
      else interromper();
    });
    observador?.observe(atelier);

    return () => {
      desmontada = true;
      observador?.disconnect();
      video.removeEventListener("playing", mostrarVideo);
      video.removeEventListener("ended", encerrarSequencia);
      video.removeEventListener("error", encerrarSequencia);
      movimentoReduzido.removeEventListener("change", aoMudarMovimento);
      ponteiroPreciso.removeEventListener("change", aoMudarPonteiro);
      document.removeEventListener("visibilitychange", aoMudarVisibilidade);
      acesso.removeEventListener("focusin", interromper);
      atelier.removeEventListener("pointermove", aoMoverPonteiro);
      atelier.removeEventListener("pointerleave", zerarDeslocamento);
      atelier.removeEventListener("pointercancel", zerarDeslocamento);
      interromper();
    };
  }, []);

  return (
    <div ref={cenaRef} className="conta-cena">
      {/* O pôster permanece sob o vídeo, inclusive sem JS ou com autoplay negado. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="conta-escultura" src="/conta/fr-escultura.webp" alt="" width={960} height={1020} fetchPriority="high" />
      <video
        ref={videoRef}
        className="conta-escultura conta-luz"
        poster="/conta/fr-escultura.webp"
        muted
        playsInline
        preload="none"
        disablePictureInPicture
        tabIndex={-1}
        hidden
      />
    </div>
  );
}
