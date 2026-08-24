"use client";

import { useEffect, useRef } from "react";

/**
 * A CAMADA 2 do vidro liquido: o realce que segue o ponteiro.
 *
 * Escreve `--px`/`--py` no proprio no, que e o que `.especular::after` le para
 * posicionar o gradiente radial. Ver DESIGN.md, secao 7, e o bloco `.especular`
 * em globals.css -- o CSS ja define o repouso (50%/0%), entao um no sem hook
 * montado mostra um brilho discreto no alto em vez de nada.
 *
 * POR QUE ESCREVER NO ESTILO E NAO EM ESTADO REACT: o ponteiro dispara dezenas
 * de eventos por segundo, e cada um viraria render da arvore inteira do sistema
 * -- em `Painel` isso re-renderizaria grafico e tabela a cada pixel do mouse.
 * `setProperty` toca so a variavel CSS, sem passar pelo React.
 *
 * OS DOIS DESLIGAMENTOS espelham exatamente as media queries do CSS:
 *
 *   - `prefers-reduced-motion` -- o realce e movimento, e a secao 6 manda
 *     desliga-lo;
 *   - `pointer: coarse` -- touch nao tem hover. Sem isto o realce ficaria aceso
 *     e PARADO no ultimo ponto tocado, que le como sujeira na tela.
 *
 * Em ambos os casos o listener nem e registrado: nao adianta esconder o efeito
 * no CSS e seguir pagando o custo do evento em JS.
 */
export function useEspecular<T extends HTMLElement>() {
  const referencia = useRef<T>(null);

  useEffect(() => {
    const no = referencia.current;
    if (!no) return;

    // `matchMedia` em vez de checar `ontouchstart`: cobre o hibrido (notebook
    // com tela de toque continua com ponteiro fino e ganha o realce).
    const semMovimento = window.matchMedia("(prefers-reduced-motion: reduce)");
    const ponteiroGrosso = window.matchMedia("(pointer: coarse)");
    if (semMovimento.matches || ponteiroGrosso.matches) return;

    let agendado = 0;

    const mover = (evento: PointerEvent) => {
      // Uma escrita por frame. Sem isto, um mouse de 1000 Hz forcaria
      // recalculo de estilo mais vezes do que a tela sabe desenhar.
      if (agendado) return;
      agendado = requestAnimationFrame(() => {
        agendado = 0;
        const caixa = no.getBoundingClientRect();
        // Caixa de dimensao zero (sistema recolhido, aba oculta) dividiria por
        // zero e escreveria `NaN%` na variavel -- valor invalido, que o CSS
        // descarta deixando o realce preso onde estava.
        if (caixa.width === 0 || caixa.height === 0) return;
        no.style.setProperty(
          "--px",
          `${((evento.clientX - caixa.left) / caixa.width) * 100}%`,
        );
        no.style.setProperty(
          "--py",
          `${((evento.clientY - caixa.top) / caixa.height) * 100}%`,
        );
      });
    };

    // Ao sair, o realce VOLTA AO REPOUSO em vez de congelar onde o ponteiro
    // deixou: brilho parado no meio da superficie nao e um estado plausivel de
    // luz e o olho registra como artefato.
    const sair = () => {
      if (agendado) cancelAnimationFrame(agendado);
      agendado = 0;
      no.style.setProperty("--px", "50%");
      no.style.setProperty("--py", "0%");
    };

    no.addEventListener("pointermove", mover);
    no.addEventListener("pointerleave", sair);

    return () => {
      if (agendado) cancelAnimationFrame(agendado);
      no.removeEventListener("pointermove", mover);
      no.removeEventListener("pointerleave", sair);
    };
  }, []);

  return referencia;
}
