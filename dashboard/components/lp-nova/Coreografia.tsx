"use client";

import { useEffect, useLayoutEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import "lenis/dist/lenis.css";
import { CHAVE_PRELOADER, POSE_INICIAL, POSES_POR_SECAO, SECOES_INDICE, formatarContador, rotuloIndice } from "@/lib/lp-nova/coreografia";
import { criarPalcoFR } from "@/lib/lp-nova/palco-fr";
import type { PalcoFR } from "@/lib/lp-nova/palco-fr";
import { ArteEstatica } from "./ArteEstatica";

const SIMBOLOS = "█▓▒░<>/_-+=#%&*";

/** A coreografia inteira da LP: o HTML vem pronto do servidor e este componente
 * so o anima. Sem JS ou com reduce, a pagina continua completa e legivel. */
export function Coreografia() {
  const canvas = useRef<HTMLCanvasElement>(null);
  const cursor = useRef<HTMLDivElement>(null);
  const indice = useRef<HTMLDivElement>(null);
  const barra = useRef<HTMLDivElement>(null);

  // Na navegacao cliente o script inline nao roda: esconde antes do paint.
  useLayoutEffect(() => {
    try {
      if (sessionStorage.getItem(CHAVE_PRELOADER)) document.documentElement.dataset.lpPre = "visto";
    } catch { /* armazenamento bloqueado: o preloader apenas toca de novo */ }
  }, []);

  useEffect(() => {
    const raiz = document.querySelector<HTMLElement>(".lp");
    const tela = canvas.current;
    if (!raiz || !tela) return;
    gsap.registerPlugin(ScrollTrigger);

    // ---------- palco 3D: o FR existente, pose conduzida pelo GSAP ----------
    const pose = { ...POSE_INICIAL };
    const mouse = { x: 0, y: 0 }, flutuacao = { y: 0 };
    // `velocidade` chega do Lenis em degraus (um pico por clique da roda);
    // `suave` e o que o FR e o letreiro leem, para nao pular a cada clique.
    const estado = { compacto: false, velocidade: 0, suave: 0, giro: 0, poeira: 0 };
    let palco: PalcoFR | null = null;
    const quadro = () => {
      if (!palco) return;
      const base = estado.compacto ? 0.55 : 1;
      palco.desenhar({
        rx: pose.rx + mouse.y * 0.12,
        ry: pose.ry + mouse.x * 0.25 + estado.giro,
        rz: pose.rz,
        x: pose.x * (estado.compacto ? 0 : 1),
        y: pose.y + flutuacao.y,
        s: pose.s * base,
        gap: pose.gap + Math.min(Math.abs(estado.suave) * 0.012, 0.7),
        inv: pose.inv,
        giroPoeira: estado.poeira,
      });
    };
    const iniciarPalco = () => {
      palco?.destruir();
      try {
        palco = criarPalcoFR(tela);
        raiz.dataset.frEstado = "pronto";
        quadro();
      } catch {
        palco = null;
        raiz.dataset.frEstado = "estatico";
      }
    };
    const perder = (evento: Event) => {
      evento.preventDefault();
      palco = null;
      raiz.dataset.frEstado = "estatico";
    };
    tela.addEventListener("webglcontextlost", perder);
    tela.addEventListener("webglcontextrestored", iniciarPalco);
    iniciarPalco();

    const mm = gsap.matchMedia();
    mm.add({
      movimento: "(prefers-reduced-motion: no-preference)",
      compacto: "(max-width: 899px)",
    }, (contexto) => {
      const { movimento, compacto } = contexto.conditions as { movimento: boolean; compacto: boolean };
      estado.compacto = compacto;
      if (!movimento) {
        // Reduce: um unico quadro parado; resize redesenha sozinho.
        Object.assign(pose, POSE_INICIAL);
        quadro();
        return;
      }
      const desfazer: (() => void)[] = [];
      const ouvir = <K extends keyof HTMLElementEventMap>(alvo: HTMLElement | Window, tipo: K, fn: (e: HTMLElementEventMap[K]) => void) => {
        alvo.addEventListener(tipo, fn as EventListener);
        desfazer.push(() => alvo.removeEventListener(tipo, fn as EventListener));
      };
      const tique = (fn: gsap.TickerCallback) => { gsap.ticker.add(fn); desfazer.push(() => gsap.ticker.remove(fn)); };

      // ---------- preloader dourado: so na primeira visita da sessao ----------
      const pre = raiz.querySelector<HTMLElement>(".lp-pre");
      const tocarPre = !!pre && document.documentElement.dataset.lpPre !== "visto";
      const atraso = tocarPre ? 1.6 : 0;

      // ---------- rolagem suave (Lenis) no ticker do GSAP ----------
      const lenis = new Lenis({ lerp: 0.09, anchors: { offset: -60 } });
      lenis.on("scroll", ScrollTrigger.update);
      const rolar = (tempo: number) => lenis.raf(tempo * 1000);
      tique(rolar);
      gsap.ticker.lagSmoothing(0);
      desfazer.push(() => { lenis.destroy(); gsap.ticker.lagSmoothing(500, 33); estado.velocidade = 0; estado.suave = 0; });

      if (tocarPre && pre) {
        const contador = pre.querySelector<HTMLElement>("[data-pre-contador]");
        const progresso = { v: 0 };
        lenis.stop();
        gsap.to(progresso, { v: 100, duration: 1.5, ease: "power2.inOut", onUpdate: () => { if (contador) contador.textContent = formatarContador(progresso.v, 3); } });
        gsap.to(pre, {
          clipPath: "inset(0 0 100% 0)", duration: 0.9, ease: "expo.inOut", delay: atraso,
          onComplete: () => {
            document.documentElement.dataset.lpPre = "visto";
            try { sessionStorage.setItem(CHAVE_PRELOADER, "1"); } catch { /* sem armazenamento */ }
          },
        });
        gsap.delayedCall(2, () => lenis.start());
      }

      // ---------- cursor proprio ----------
      const cur = cursor.current;
      if (cur) {
        const cx = gsap.quickTo(cur, "x", { duration: 0.35, ease: "power3" });
        const cy = gsap.quickTo(cur, "y", { duration: 0.35, ease: "power3" });
        ouvir(window, "pointermove", (e) => { cx(e.clientX); cy(e.clientY); });
        raiz.querySelectorAll<HTMLElement>("a, .pn").forEach((alvo) => {
          ouvir(alvo, "pointerenter", () => gsap.to(cur, { scale: 2.4, duration: 0.3 }));
          ouvir(alvo, "pointerleave", () => gsap.to(cur, { scale: 1, duration: 0.3 }));
        });
      }

      // ---------- texto embaralhado ----------
      const embaralhar = (el: HTMLElement) => {
        const original = el.dataset.texto ?? (el.dataset.texto = el.textContent ?? "");
        const p = { v: 0 };
        gsap.to(p, {
          v: 1, duration: 0.7, ease: "none", overwrite: true,
          onUpdate: () => {
            const n = Math.floor(p.v * original.length);
            el.textContent = original.slice(0, n) + [...original.slice(n)].map((c) => c === " " ? " " : SIMBOLOS[(Math.random() * SIMBOLOS.length) | 0]).join("");
          },
          onComplete: () => { el.textContent = original; },
        });
      };
      raiz.querySelectorAll<HTMLElement>("[data-embaralhar]").forEach((el) => {
        // O nome acessivel nao pode virar ruido durante os 700ms.
        if (el.tagName === "A") el.setAttribute("aria-label", el.textContent ?? "");
        if (el.classList.contains("tag")) ScrollTrigger.create({ trigger: el, start: "top 92%", once: true, onEnter: () => embaralhar(el) });
        else ouvir(el, "pointerenter", () => embaralhar(el));
      });
      desfazer.push(() => raiz.querySelectorAll<HTMLElement>("[data-texto]").forEach((el) => { el.textContent = el.dataset.texto ?? el.textContent; }));

      // ---------- letreiro: velocidade e sentido seguem a rolagem ----------
      const letreiro = raiz.querySelector<HTMLElement>("[data-letreiro]");
      if (letreiro) {
        const giro = gsap.to(letreiro, { xPercent: -50, duration: 20, ease: "none", repeat: -1 });
        tique(() => {
          const v = estado.suave;
          giro.timeScale(gsap.utils.interpolate(giro.timeScale(), (v < 0 ? -1 : 1) * (1 + Math.abs(v) * 0.35), 0.1));
          gsap.set(letreiro, { skewX: gsap.utils.clamp(-12, 12, v * -0.6) });
        });
      }

      // ---------- FR: abertura, flutuacao, paralaxe e quadro por tique ----------
      gsap.from(pose, { gap: 2.8, ry: -3.4, s: 0.4, duration: 2.2, delay: atraso, ease: "power3.out" });
      gsap.to(flutuacao, { y: 0.18, duration: 2.6, yoyo: true, repeat: -1, ease: "sine.inOut" });
      const qx = gsap.quickTo(mouse, "x", { duration: 1.2 }), qy = gsap.quickTo(mouse, "y", { duration: 1.2 });
      ouvir(window, "pointermove", (e) => { qx(e.clientX / innerWidth - 0.5); qy(e.clientY / innerHeight - 0.5); });
      tique(() => {
        // deltaRatio: em tela de 120 Hz a poeira nao gira no dobro da velocidade.
        const passo = gsap.ticker.deltaRatio(60);
        // Lido a cada quadro, nao no evento: parado, o Lenis nem sempre emite o zero final.
        estado.velocidade = lenis.velocity;
        estado.suave += (estado.velocidade - estado.suave) * (1 - 0.92 ** passo);
        const v = estado.suave;
        estado.giro = (estado.giro + v * 0.0006 * passo) * 0.95 ** passo;
        estado.poeira += (0.0015 + Math.abs(v) * 0.0006) * passo;
        quadro();
      });
      desfazer.push(() => { estado.giro = 0; Object.assign(mouse, { x: 0, y: 0 }); flutuacao.y = 0; });

      // ---------- entrada do topo e do heroi ----------
      gsap.from([".lp-cabecalho", "#inicio .rv"], { y: 24, opacity: 0, duration: 0.9, stagger: 0.1, delay: atraso + 0.7, ease: "power3.out" });
      gsap.from("h1 .w > span", { yPercent: 115, duration: 1.1, stagger: 0.07, delay: atraso + 0.4, ease: "power4.out" });
      raiz.querySelectorAll<HTMLElement>("[data-n]").forEach((el) => {
        const alvo = Number(el.dataset.n), contagem = { v: 0 };
        el.textContent = formatarContador(0, 2);
        gsap.to(contagem, { v: alvo, duration: 1.8, delay: atraso + 1, ease: "power2.out", onUpdate: () => { el.textContent = formatarContador(contagem.v, 2); } });
      });

      // ---------- vitrine horizontal fixada: TEXTO -> EMOJIS -> TEMPO ----------
      const trilho = raiz.querySelector<HTMLElement>("#faixa .trk");
      if (trilho) {
        const distancia = () => trilho.scrollWidth - innerWidth;
        gsap.to(trilho, { x: () => -distancia(), ease: "none", scrollTrigger: { trigger: "#faixa", pin: true, scrub: 1, end: () => `+=${distancia()}`, invalidateOnRefresh: true } });
      }

      // ---------- heroi se dissolve; indice lateral; barra de progresso ----------
      gsap.to("#inicio .blk", { yPercent: -25, opacity: 0, ease: "none", scrollTrigger: { trigger: "#inicio", start: "top top", end: "bottom top", scrub: true } });
      SECOES_INDICE.forEach((id, i) => ScrollTrigger.create({
        trigger: `#${id}`, start: "top 50%", end: "bottom 50%",
        onToggle: (s) => { if (s.isActive && indice.current) indice.current.textContent = rotuloIndice(i); },
      }));
      if (barra.current) gsap.fromTo(barra.current, { scaleX: 0 }, { scaleX: 1, ease: "none", scrollTrigger: { start: 0, end: "max", scrub: 0.3 } });

      // ---------- fecho: o mundo vira ouro e o FR, relevo do proprio ouro ----------
      gsap.to(pose, {
        inv: 1, ease: "none",
        scrollTrigger: { trigger: "#fecho", start: "top 70%", end: "top 20%", scrub: true, onUpdate: (s) => raiz.classList.toggle("inv", s.progress > 0.5) },
      });
      desfazer.push(() => raiz.classList.remove("inv"));

      // ---------- a rolagem conduz a pose do FR ----------
      // Cada pose chega junto com a propria secao (nao com a fracao do <main>):
      // a faixa fixada ocupa duas telas e desalinharia uma timeline unica.
      POSES_POR_SECAO.forEach((alvo, i) => {
        const anterior = i === 0 ? POSE_INICIAL : POSES_POR_SECAO[i - 1];
        const { rx, ry, rz, x, s, gap } = anterior;
        gsap.fromTo(pose, { rx, ry, rz, x, s, gap }, {
          ...alvo, ease: "power2.inOut", immediateRender: false,
          scrollTrigger: { trigger: `#${SECOES_INDICE[i + 1]}`, start: "top 85%", end: "top 15%", scrub: 1.2 },
        });
      });

      // ---------- titulos, revelacoes, frase e reguas ----------
      raiz.querySelectorAll("h2").forEach((h) => gsap.from(h.querySelectorAll(".w > span"), { yPercent: 115, duration: 0.9, stagger: 0.06, ease: "power4.out", scrollTrigger: { trigger: h, start: "top 85%" } }));
      const revelar = gsap.utils.toArray<HTMLElement>("section:not(#inicio) .rv");
      gsap.set(revelar, { y: 36, opacity: 0 });
      ScrollTrigger.batch(revelar, { start: "top 88%", once: true, onEnter: (lote) => gsap.to(lote, { y: 0, opacity: 1, stagger: 0.1, duration: 0.8, ease: "power3.out" }) });
      gsap.from("[data-letras] > span", { opacity: 0, y: 20, stagger: 0.05, duration: 0.5, scrollTrigger: { trigger: ".quote", start: "top 85%" } });
      gsap.fromTo("[data-regua]", { scaleX: 0 }, { scaleX: 1, ease: "none", scrollTrigger: { trigger: "[data-regua]", start: "top 90%", end: "top 40%", scrub: true } });
      gsap.fromTo("[data-passos]", { scaleY: 0 }, { scaleY: 1, ease: "none", scrollTrigger: { trigger: ".steps", start: "top 65%", end: "bottom 60%", scrub: true } });
      gsap.utils.toArray<HTMLElement>(".step").forEach((passo) => gsap.from(passo, { opacity: 0.2, x: -18, ease: "none", scrollTrigger: { trigger: passo, start: "top 85%", end: "top 60%", scrub: true } }));

      // ---------- botoes magneticos ----------
      raiz.querySelectorAll<HTMLElement>(".mag").forEach((botao) => {
        const x = gsap.quickTo(botao, "x", { duration: 0.4, ease: "power3" }), y = gsap.quickTo(botao, "y", { duration: 0.4, ease: "power3" });
        ouvir(botao, "pointermove", (e) => { const r = botao.getBoundingClientRect(); x((e.clientX - r.left - r.width / 2) * 0.3); y((e.clientY - r.top - r.height / 2) * 0.3); });
        ouvir(botao, "pointerleave", () => { x(0); y(0); });
      });

      // Fontes e imagens mudam alturas depois do primeiro calculo.
      void document.fonts?.ready.then(() => ScrollTrigger.refresh());

      return () => desfazer.forEach((fn) => fn());
    });

    return () => {
      mm.revert();
      tela.removeEventListener("webglcontextlost", perder);
      tela.removeEventListener("webglcontextrestored", iniciarPalco);
      palco?.destruir();
      palco = null;
    };
  }, []);

  return (
    <>
      <div className="lp-barra" ref={barra} aria-hidden="true" />
      <div className="lp-cursor" ref={cursor} aria-hidden="true" />
      <div className="lp-indice" ref={indice} aria-hidden="true">{rotuloIndice(0)}</div>
      <div className="lp-palco" aria-hidden="true">
        <div className="lp-palco-estatico"><ArteEstatica /></div>
        <canvas ref={canvas} className="lp-gl" />
      </div>
    </>
  );
}
