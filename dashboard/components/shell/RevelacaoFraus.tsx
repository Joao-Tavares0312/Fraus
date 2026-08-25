"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useReducedMotion } from "motion/react";
import { type LeituraDeCliques, timecodeDe, vereditoDe } from "@/lib/pontuarCliques";
import { cn } from "@/lib/utils";

/**
 * A REVELACAO -- o unico lugar do Fraus onde o DESIGN.md nao manda.
 *
 * O resto da interface e modo Operate: expressao nunca obscurece a tarefa, o
 * movimento comunica estado e nada anima por ter montado. Aqui, nao. Este
 * painel e um segredo que exige cinco cliques deliberados para existir, dura
 * segundos, nao carrega tarefa nenhuma e some sozinho -- e o unico ponto da
 * aplicacao onde a coleira sai, por decisao explicita de 25/08/2026.
 *
 * NAO E UM MUNDO NOVO, e isso importa: o vocabulario ja existia. O tema "chuva
 * de neon" (DESIGN.md secao 8) ja tem grade a laser, tubo magenta e tubo ciano.
 * O que este painel faz e SOLTAR o que o Operate mantinha contido, nao inventar
 * uma estetica de fora.
 *
 * DUAS PECAS, e elas fazem coisas diferentes:
 *
 * 1. A FITA ESTRAGADA (a pele) -- grade fugindo ao horizonte, sol partido por
 *    scanlines, aberracao cromatica no monograma, tremor de tracking. CSS puro,
 *    sem WebGL: roda em qualquer maquina de banca sem risco de engasgo.
 * 2. O REPLAY (o significado) -- os chips de latencia entram UM A UM, no
 *    intervalo REAL em que a pessoa clicou. Voce levou 1,2 s no terceiro? O
 *    terceiro chip demora 1,2 s. E a unica parte disto que nenhum outro projeto
 *    poderia copiar, porque so o Fraus mede tempo -- a espera nao e enfeite,
 *    e a propria medicao sendo executada de volta na cara de quem a produziu.
 *
 * `prefers-reduced-motion` DESLIGA TUDO e nao esconde nada: sem grade animada,
 * sem tremor, sem replay e sem digitacao -- todos os chips e o veredito inteiro
 * aparecem de uma vez. O segredo nao e privilegio de quem tolera movimento.
 */

/** Quanto o painel fica de pe depois que o replay termina. */
const RESPIRO_APOS_O_REPLAY_MS = 8_000;

/** Velocidade da maquina de escrever do veredito. */
const MS_POR_CARACTERE = 28;


export function RevelacaoFraus({
  leitura,
  aoFechar,
}: {
  leitura: LeituraDeCliques | null;
  aoFechar: () => void;
}) {
  const painel = useRef<HTMLDivElement>(null);
  const semMovimento = useReducedMotion();

  const veredito = leitura ? vereditoDe(leitura) : "";

  // Quantos chips ja entraram. Com movimento reduzido, todos de uma vez.
  const [chipsVisiveis, setChipsVisiveis] = useState(
    semMovimento ? (leitura?.latenciasMs.length ?? 0) : 0,
  );
  const [digitados, setDigitados] = useState(
    semMovimento ? veredito.length : 0,
  );

  // O REPLAY. Cada chip entra depois da latencia que ele mesmo representa --
  // e o que faz o painel reproduzir o ritmo em vez de descreve-lo. Os
  // temporizadores sao encadeados por acumulo em vez de um intervalo fixo,
  // porque os intervalos sao desiguais por definicao: a desigualdade E o dado.
  useEffect(() => {
    if (semMovimento || !leitura) return;
    const relogios: ReturnType<typeof setTimeout>[] = [];
    let acumulado = 0;
    leitura.latenciasMs.forEach((ms, i) => {
      acumulado += ms;
      relogios.push(setTimeout(() => setChipsVisiveis(i + 1), acumulado));
    });
    return () => relogios.forEach(clearTimeout);
  }, [leitura, semMovimento]);

  /** A duracao REAL da sequencia de cliques -- vai para o timecode da fita. */
  const duracaoTotal =
    leitura?.latenciasMs.reduce((soma, ms) => soma + ms, 0) ?? 0;

  /** Quanto o replay leva. Com movimento reduzido nao ha replay: e zero. */
  const duracaoDoReplay = semMovimento ? 0 : duracaoTotal;

  // A DIGITACAO do veredito, depois que o replay termina.
  useEffect(() => {
    if (semMovimento || !veredito) return;
    const relogios: ReturnType<typeof setTimeout>[] = [];
    for (let i = 1; i <= veredito.length; i += 1) {
      relogios.push(
        setTimeout(() => setDigitados(i), duracaoDoReplay + i * MS_POR_CARACTERE),
      );
    }
    return () => relogios.forEach(clearTimeout);
  }, [veredito, duracaoDoReplay, semMovimento]);

  useEffect(() => {
    painel.current?.focus();
    // O fechamento automatico espera o replay TERMINAR antes de contar o
    // respiro. Com um teto fixo de 8s, um ritmo lento (a janela do contador
    // permite ate 2s por clique, logo 8s de replay) faria o painel sumir na
    // mesma hora em que o veredito aparecesse.
    const encerra = setTimeout(
      aoFechar,
      duracaoDoReplay + veredito.length * MS_POR_CARACTERE + RESPIRO_APOS_O_REPLAY_MS,
    );
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key === "Escape") aoFechar();
    }
    document.addEventListener("keydown", aoTeclar);
    return () => {
      clearTimeout(encerra);
      document.removeEventListener("keydown", aoTeclar);
    };
  }, [aoFechar, duracaoDoReplay, veredito.length]);

  // Sem guarda de montagem: este componente so existe depois de cinco cliques,
  // entao nunca aparece no render do servidor e `document` sempre esta la.
  //
  // Por PORTAL no <body>: a marca mora dentro da barra lateral, que usa
  // `transform` para recolher, e ancestral com transform vira o bloco de
  // contencao de qualquer descendente `position: fixed`.
  return createPortal(
    <div
      className="fenda-cena fixed inset-0 z-50 flex items-center justify-center overflow-hidden p-4"
      data-parado={semMovimento ? "" : undefined}
      onClick={aoFechar}
    >
      <EstiloDaCena />

      {/* A GRADE A LASER fugindo ao horizonte, e o sol atras dela. Sao fundo:
          `aria-hidden`, sem conteudo, e nao roubam foco nem leitura. */}
      <div className="fenda-ceu" aria-hidden />
      <div className="fenda-sol" aria-hidden />
      <div className="fenda-horizonte" aria-hidden />
      <div className="fenda-grade" aria-hidden />
      <div className="fenda-scanlines" aria-hidden />

      {/* TRAVA 3 do easter egg: o selo e INESCAPAVEL enquanto a tela mente.
          Nao existe captura de tela da dashboard mentindo sem ele dentro. */}
      <p
        role="alert"
        className="fenda-selo absolute top-6 left-1/2 -translate-x-1/2 border px-4 py-2 text-[0.6875rem] font-semibold tracking-[0.25em] uppercase"
      >
        Fraus está mentindo nesta tela
      </p>

      <div
        ref={painel}
        role="dialog"
        aria-modal="true"
        aria-label="Fraus leu os seus cliques"
        tabIndex={-1}
        onClick={(evento) => evento.stopPropagation()}
        className="fenda-painel relative w-full max-w-lg outline-none"
      >
        {/* A CABECA DE FITA. Timecode nao e fantasia aqui: este produto MEDE
            TEMPO, e o numero da direita e a duracao real da sequencia de
            cliques em quadros de 1/25 s. E a peca que faz a caixa ler como fita
            em vez de retangulo arredondado com neon em volta. */}
        <div className="fenda-cabeca" aria-hidden>
          <span className="fenda-rec">
            <i />
            REC
          </span>
          <span className="fenda-timecode">{timecodeDe(duracaoTotal)}</span>
        </div>

        <div className="fenda-corpo">
          {/* O MONOGRAMA com aberracao cromatica: tres copias empilhadas,
              magenta e ciano deslocadas 2px para os lados. As duas de tras sao
              aria-hidden -- o leitor de tela recebe UMA palavra, nao tres. */}
          <p className="fenda-marca relative text-center">
            <span className="fenda-marca-c" aria-hidden>
              FRAVS
            </span>
            <span className="fenda-marca-m" aria-hidden>
              FRAVS
            </span>
            <span className="fenda-marca-t">FRAVS</span>
          </p>

        {leitura ? (
          <>
            <p className="fenda-legenda mt-6">
              Os seus cinco cliques têm horário. São uma conversa:
            </p>

            {/* Os chips entram NO RITMO REAL -- ver o efeito do replay acima.
                `min-h` reservado para a linha nao crescer enquanto eles chegam:
                layout que pula denunciaria a encenacao como falha de render. */}
            <ul className="fenda-fita mt-3 flex min-h-[2.25rem] flex-wrap items-center gap-2">
              {leitura.latenciasMs.map((ms, i) => (
                <li
                  key={i}
                  className={cn(
                    "fenda-chip num",
                    i === leitura.indiceDaHesitacao && "fenda-chip-hesitou",
                    i < chipsVisiveis && "fenda-chip-dentro",
                  )}
                >
                  {ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`}
                  {i === leitura.indiceDaHesitacao ? " ◂" : ""}
                </li>
              ))}
            </ul>

            <p className="fenda-placar mt-7">
              <span className="fenda-numero num">{leitura.leitura}</span>
              <span className="fenda-de-cem num">/ 100</span>
            </p>

            {/* A RESSALVA. Ela NAO e nota de rodape e nao pode ser tratada como
                enfeite: e o que separa uma piada honesta do projeto mentindo
                sobre a propria metodologia. Fica em contraste de leitura,
                nunca em neon. */}
            <p className="fenda-ressalva mt-3">
              Só o <strong>sinal de tempo</strong> — sem texto, sem emoji, sem
              modelo. Não é o score do Fraus, e não vira nota nem categoria.
            </p>

            <p className="fenda-veredito mt-7">
              {semMovimento ? veredito : veredito.slice(0, digitados)}
              {!semMovimento && digitados < veredito.length ? (
                <span className="fenda-cursor" aria-hidden />
              ) : null}
            </p>
            <p className="fenda-acusacao mt-2">
              E o que você diria, se eu perguntasse? Que gostou.
            </p>
          </>
        ) : (
          // Sem latencia nao ha leitura, e leitura sem dado seria numero
          // inventado -- a invariante 2 vale inclusive dentro do easter egg.
          <p className="fenda-veredito mt-7">
            Não consegui medir o seu ritmo. Sem dado, não invento número — nem
            aqui.
          </p>
        )}

          <p className="fenda-cicero mt-8">
            <em>Erebo et Nocte nata</em> — filha do Escuro e da Noite, irmã de{" "}
            <strong>Dolus</strong> e de <strong>Metus</strong>. Cícero,{" "}
            <em>De Natura Deorum</em> III.17
          </p>
        </div>
      </div>
    </div>,
    document.body,
  );
}

/**
 * O estilo da cena, no proprio componente e nao no `globals.css`.
 *
 * DE PROPOSITO: nada disto pertence ao sistema de design. Sao regras de um
 * segredo que dura segundos, e deixa-las no `globals.css` as ofereceria como
 * vocabulario reutilizavel -- que e exatamente o que elas nao sao. Some o
 * componente, some o estilo.
 */
function EstiloDaCena() {
  return (
    <style>{`
      /* A cena inteira e um degrade de noite: quase-preto no topo, roxo
         profundo no meio, e a fogueira magenta na linha do horizonte. */
      .fenda-cena {
        background:
          radial-gradient(120% 70% at 50% 100%, oklch(0.42 0.22 330 / 0.55) 0%, transparent 60%),
          linear-gradient(180deg, oklch(0.09 0.04 300) 0%, oklch(0.14 0.09 310) 55%, oklch(0.22 0.14 320) 100%);
      }

      /* O SOL: disco cortado por faixas horizontais -- o corte e o que o
         distingue de um circulo com degrade, e e a assinatura do genero.

         GRANDE O BASTANTE PARA SOBRAR DO PAINEL, e isto e conserto de uma coisa
         que so a tela mostrou: com 30rem ele tinha exatamente a largura da
         caixa (max-w-lg = 32rem) e ficava inteiro escondido atras dela. O
         elemento mais reconhecivel do genero existia no CSS e nao na imagem.
         Agora ele transborda dos dois lados e por cima, e a caixa recorta o
         meio dele -- que e uma composicao melhor do que a original.

         O corte tambem ABRE com a distancia (faixas mais largas embaixo,
         apertando para cima) em vez de ser regular: o degrade de mascara
         acompanha o disco em vez de listra-lo uniformemente. */
      .fenda-sol {
        position: absolute;
        left: 50%;
        bottom: 22%;
        width: min(46rem, 92vw);
        aspect-ratio: 1;
        translate: -50% 0;
        border-radius: 50%;
        background: linear-gradient(180deg, oklch(0.9 0.19 80) 0%, oklch(0.76 0.25 35) 42%, oklch(0.62 0.29 350) 78%, oklch(0.45 0.26 320) 100%);
        -webkit-mask-image:
          repeating-linear-gradient(180deg, #000 0 14px, transparent 14px 20px),
          linear-gradient(180deg, transparent 0%, #000 26%);
        -webkit-mask-composite: source-in;
        mask-image:
          repeating-linear-gradient(180deg, #000 0 14px, transparent 14px 20px),
          linear-gradient(180deg, transparent 0%, #000 26%);
        mask-composite: intersect;
        opacity: 0.72;
      }

      /* A LINHA DO HORIZONTE acesa, onde o sol encontra a grade. Sem ela as
         duas pecas so se sobrepoem; com ela existe um chao. */
      .fenda-horizonte {
        position: absolute;
        left: 0;
        right: 0;
        bottom: 26%;
        height: 1px;
        background: linear-gradient(90deg, transparent, oklch(0.88 0.2 330) 30%, oklch(0.92 0.16 200) 50%, oklch(0.88 0.2 330) 70%, transparent);
        box-shadow: 0 0 24px 4px oklch(0.7 0.24 330 / 0.55);
      }

      /* O CEU acima do horizonte, para o sol nao encostar direto no degrade. */
      .fenda-ceu {
        position: absolute;
        inset: 0 0 26% 0;
        background: radial-gradient(80% 100% at 50% 100%, oklch(0.5 0.2 340 / 0.35), transparent 70%);
      }

      /* A GRADE A LASER. Duas familias de linha em perspectiva: as que fogem ao
         ponto de fuga e as horizontais comprimindo com a distancia. A animacao
         desloca so a familia horizontal, e e o que produz a sensacao de avanco
         sem nada se mover de lugar. */
      .fenda-grade {
        position: absolute;
        inset: 74% 0 0 0;
        perspective: 14rem;
        overflow: hidden;
        /* A mascara APAGA A FAIXA DO HORIZONTE, e nao so a borda de cima. Sem
           isso, as linhas que fogem ao ponto de fuga comprimem umas nas outras
           ate virarem um risco vertical solido no centro -- observado na tela, e
           ele lia como defeito de render, nao como grade. Fazer a grade nascer
           JA a alguma distancia resolve na raiz: um chao real tambem nao mostra
           detalhe no infinito. */
        -webkit-mask-image: linear-gradient(180deg, transparent 0%, transparent 8%, #000 34%, #000 100%);
        mask-image: linear-gradient(180deg, transparent 0%, transparent 8%, #000 34%, #000 100%);
      }
      .fenda-grade::before {
        content: "";
        position: absolute;
        inset: -60% -60% -20% -60%;
        transform: rotateX(74deg);
        background:
          repeating-linear-gradient(90deg, oklch(0.82 0.18 200 / 0.5) 0 1px, transparent 1px 4.5rem),
          repeating-linear-gradient(0deg, oklch(0.72 0.24 330 / 0.55) 0 1px, transparent 1px 3rem);
        animation: fenda-avanco 2.6s linear infinite;
      }
      @keyframes fenda-avanco {
        to { background-position: 0 0, 0 3rem; }
      }

      /* As SCANLINES por cima de tudo, inclusive do painel: e o que unifica a
         cena como uma imagem CAPTADA, e nao como camadas empilhadas.

         multiply estava errado e nao aparecia: multiplicar preto sobre um
         fundo que ja e quase preto nao escurece nada. O que uma varredura de
         tubo faz e alternar linha acesa e linha apagada, entao a faixa clara
         entra por screen e a escura por opacidade -- duas camadas, e agora
         elas existem na imagem. */
      .fenda-scanlines {
        position: absolute;
        inset: 0;
        pointer-events: none;
        background:
          repeating-linear-gradient(180deg, oklch(1 0 0 / 0.045) 0 1px, transparent 1px 3px),
          repeating-linear-gradient(180deg, transparent 0 2px, oklch(0 0 0 / 0.42) 2px 3px);
      }

      .fenda-selo {
        color: oklch(0.78 0.2 25);
        border-color: oklch(0.65 0.22 25);
        background: oklch(0.16 0.08 20 / 0.85);
        box-shadow: 0 0 0 1px oklch(0.16 0.08 20), 0 6px 22px oklch(0.1 0.05 20 / 0.7);
        backdrop-filter: blur(2px);
      }

      /* O PAINEL: vidro escuro com dois fios de neon -- ciano em cima, magenta
         embaixo, que sao os dois tubos do tema "chuva de neon". */
      .fenda-painel {
        background: oklch(0.12 0.05 305 / 0.86);
        border: 1px solid oklch(0.62 0.2 330 / 0.55);
        border-radius: 0.25rem;
        backdrop-filter: blur(14px) saturate(1.3);
        box-shadow:
          inset 0 -1px 0 oklch(0.72 0.26 330 / 0.6),
          0 24px 70px oklch(0.05 0.04 320 / 0.75);
        overflow: hidden;
      }
      .fenda-corpo { padding: 1.75rem 2rem 2rem; }
      @media (min-width: 640px) { .fenda-corpo { padding: 2rem 2.5rem 2.5rem; } }

      /* A CABECA DE FITA. Barra de status na borda de cima, no ciano do tubo --
         e o que separa "caixa com neon em volta" de "isto e uma fita". */
      .fenda-cabeca {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.5rem 0.875rem;
        border-bottom: 1px solid oklch(0.62 0.16 200 / 0.4);
        background: oklch(0.18 0.06 250 / 0.55);
        font-size: 0.625rem;
        letter-spacing: 0.22em;
        font-weight: 600;
      }
      .fenda-rec {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        color: oklch(0.8 0.19 25);
      }
      .fenda-rec i {
        width: 0.4rem;
        height: 0.4rem;
        border-radius: 50%;
        background: oklch(0.68 0.24 25);
        box-shadow: 0 0 8px oklch(0.68 0.24 25);
        animation: fenda-piscar 1.4s steps(1, end) infinite;
      }
      .fenda-timecode {
        font-family: var(--font-mono, ui-monospace, monospace);
        font-variant-numeric: tabular-nums;
        letter-spacing: 0.14em;
        color: oklch(0.86 0.13 200);
      }

      /* O PLACAR: a base do "/ 100" assenta na base do numerao. items-baseline
         do flex nao resolvia sozinho porque line-height: 0.9 no numero
         desloca a caixa de texto em relacao a base optica. */
      .fenda-placar {
        display: flex;
        align-items: last baseline;
        gap: 0.6rem;
      }

      /* O MONOGRAMA e a ABERRACAO CROMATICA. As tres copias ocupam o mesmo
         lugar; as de tras vazam 2px para os lados em magenta e ciano. */
      .fenda-marca {
        font-size: clamp(2.75rem, 11vw, 4.25rem);
        font-weight: 700;
        letter-spacing: 0.28em;
        line-height: 1;
        text-indent: 0.28em; /* compensa o tracking do ultimo glifo */
      }
      .fenda-marca-t { display: block; color: oklch(0.97 0.02 300); }
      .fenda-marca-m,
      .fenda-marca-c {
        position: absolute;
        inset: 0;
        display: block;
        mix-blend-mode: screen;
      }
      /* O deslocamento de repouso mora NO ELEMENTO, e nao so nos quadros: com
         animation: none (movimento reduzido) e ele que sobrevive, e sem ele a
         aberracao sumiria justamente para quem so pode ve-la parada. Enquanto a
         animacao roda, os quadros vencem -- e o que se quer. */
      .fenda-marca-m { color: oklch(0.68 0.28 330); translate: -2px 0; }
      .fenda-marca-c { color: oklch(0.82 0.17 200); translate: 2px 0; }

      /* O TRACKING ERROR: passos secos, nunca interpolados -- fita estragada
         SALTA, nao desliza, e steps() e o que separa os dois.

         CADA COPIA TEM O SEU PROPRIO QUADRO-CHAVE, e nao o mesmo com
         reverse: a magenta descansa a -2px e a ciano a +2px, entao reusar os
         mesmos quadros jogaria as duas para o mesmo lado e a franja sumiria de
         uma das bordas. */
      .fenda-marca-m { animation: fenda-tracking-m 3.1s steps(1, end) infinite; }
      .fenda-marca-c { animation: fenda-tracking-c 3.1s steps(1, end) infinite; }
      @keyframes fenda-tracking-m {
        0%, 88%   { translate: -2px 0; }
        90%       { translate: -8px 1px; }
        92%       { translate: 4px -1px; }
        94%       { translate: -5px 0; }
        96%, 100% { translate: -2px 0; }
      }
      @keyframes fenda-tracking-c {
        0%, 88%   { translate: 2px 0; }
        90%       { translate: 7px -1px; }
        92%       { translate: -3px 1px; }
        94%       { translate: 5px 0; }
        96%, 100% { translate: 2px 0; }
      }

      .fenda-legenda,
      .fenda-cicero {
        color: oklch(0.79 0.04 300);
        font-size: 0.75rem;
        line-height: 1.5;
      }
      .fenda-cicero strong { color: oklch(0.93 0.03 300); font-weight: 600; }

      /* Os CHIPS da fita. Nascem apagados e deslocados; fenda-chip-dentro
         entra pelo replay, um a um, no intervalo real de cada latencia. */
      .fenda-chip {
        border: 1px solid oklch(0.62 0.14 200 / 0.5);
        background: oklch(0.2 0.06 250 / 0.55);
        color: oklch(0.88 0.1 200);
        padding: 0.3rem 0.6rem;
        font-size: 0.75rem;
        border-radius: 0.125rem;
        opacity: 0;
        translate: 0 6px;
        filter: blur(3px);
        transition: opacity 260ms ease-out, translate 260ms ease-out, filter 260ms ease-out;
      }
      .fenda-chip-dentro { opacity: 1; translate: 0 0; filter: blur(0); }
      .fenda-chip-hesitou {
        border-color: oklch(0.68 0.24 25 / 0.85);
        background: oklch(0.24 0.1 20 / 0.6);
        color: oklch(0.84 0.16 30);
        box-shadow: 0 0 18px oklch(0.6 0.22 25 / 0.45);
      }

      .fenda-numero {
        font-size: 3.75rem;
        font-weight: 700;
        line-height: 0.9;
        color: oklch(0.97 0.02 300);
        text-shadow: 0 0 26px oklch(0.7 0.26 330 / 0.65), 0 0 60px oklch(0.7 0.26 330 / 0.3);
      }
      .fenda-de-cem { font-size: 0.875rem; color: oklch(0.75 0.05 300); }

      /* A RESSALVA fica em cinza LEGIVEL, nunca em neon: ela e a peca honesta
         do painel e nao pode competir com a encenacao nem sumir nela. */
      .fenda-ressalva {
        color: oklch(0.78 0.03 300);
        font-size: 0.6875rem;
        line-height: 1.5;
        max-width: 44ch;
      }
      .fenda-ressalva strong { color: oklch(0.93 0.02 300); font-weight: 600; }

      .fenda-veredito {
        color: oklch(0.96 0.02 300);
        font-size: 1rem;
        line-height: 1.5;
        min-height: 1.5rem;
        border-top: 1px solid oklch(0.62 0.2 330 / 0.3);
        padding-top: 1.25rem;
      }
      .fenda-acusacao { color: oklch(0.8 0.04 300); font-size: 0.9375rem; }

      /* O CURSOR de bloco da maquina de escrever. */
      .fenda-cursor {
        display: inline-block;
        width: 0.5em;
        height: 1.05em;
        margin-left: 0.12em;
        vertical-align: text-bottom;
        background: oklch(0.82 0.17 200);
        animation: fenda-piscar 1s steps(1, end) infinite;
      }
      @keyframes fenda-piscar { 50% { opacity: 0; } }

      /* PARADO: a cena inteira congela. Nada de grade avancando, nada de
         tracking, nada de cursor piscando -- e o replay ja entregou todos os
         chips de uma vez, pelo estado do componente. O segredo nao e
         privilegio de quem tolera movimento. */
      .fenda-cena[data-parado] .fenda-grade::before,
      .fenda-cena[data-parado] .fenda-marca-m,
      .fenda-cena[data-parado] .fenda-marca-c,
      .fenda-cena[data-parado] .fenda-cursor {
        animation: none;
      }
      .fenda-cena[data-parado] .fenda-chip { transition: none; }

      @media (prefers-reduced-motion: reduce) {
        .fenda-grade::before,
        .fenda-marca-m,
        .fenda-marca-c,
        .fenda-cursor { animation: none; }
        .fenda-chip { transition: none; }
      }
    `}</style>
  );
}
