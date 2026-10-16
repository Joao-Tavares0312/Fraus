"use client";

import { useId, useRef, useState } from "react";
import type { RefObject } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { Check, Shuffle, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const PECAS = ["Topo", "Centro", "Base"];
const DESAFIOS = [[-3, 2, -1], [2, -3, 3], [-1, 3, -2], [3, 1, -3]];

function descreverPosicao(posicao: number) {
  if (posicao === 0) return "Encaixada";
  const passos = Math.abs(posicao);
  return `${passos} ${passos === 1 ? "passo" : "passos"} à ${posicao < 0 ? "esquerda" : "direita"}`;
}

/** Brincadeira local: nao le dados, nao mede a pessoa e nao altera indicadores. */
export function SegredoFraus({
  aoFechar,
  gatilho,
}: {
  aoFechar: () => void;
  gatilho: RefObject<HTMLButtonElement | null>;
}) {
  const id = useId();
  const fechar = useRef<HTMLButtonElement>(null);
  const [desafio, setDesafio] = useState(0);
  const [posicoes, setPosicoes] = useState(DESAFIOS[0]);
  const encaixadas = posicoes.filter((posicao) => posicao === 0).length;
  const resolvido = encaixadas === PECAS.length;

  function embaralhar() {
    const proximo = (desafio + 1) % DESAFIOS.length;
    setDesafio(proximo);
    setPosicoes(DESAFIOS[proximo]);
  }

  return (
    <Dialog.Root open onOpenChange={(aberto) => { if (!aberto) aoFechar(); }}>
      <Dialog.Portal>
        {/* Base UI omite o backdrop aninhado por padrao; aqui o clique nao deve chegar a gaveta. */}
        <Dialog.Backdrop forceRender className="fixed inset-0 z-[60] bg-black/65" />
        <Dialog.Popup
          initialFocus={fechar}
          finalFocus={gatilho}
          className="fixed top-1/2 left-1/2 z-[60] max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-3xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-border bg-popover p-5 text-popover-foreground shadow-xl outline-none sm:p-8"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="text-2xl font-medium sm:text-3xl">Encaixe secreto</Dialog.Title>
              <Dialog.Description className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted-foreground">
                Três fragmentos. Uma marca. Deslize as peças até reconstruir o FR.
              </Dialog.Description>
            </div>
            <Dialog.Close render={<Button ref={fechar} variant="ghost" size="icon" className="size-11 shrink-0" />} aria-label="Fechar segredo">
              <X aria-hidden />
            </Dialog.Close>
          </div>

          <div className="mt-6 grid items-center gap-6 sm:grid-cols-[1.15fr_1fr] sm:gap-8">
            <div className="overflow-hidden rounded-lg border border-border bg-background">
              <svg viewBox="-96 0 992 640" className="block w-full" role="img" aria-label={resolvido ? "Monograma FR reconstruído" : "Monograma FR dividido em três fragmentos horizontais"}>
                <defs>
                  {PECAS.map((peca, indice) => (
                    <clipPath key={peca} id={`${id}-recorte-${indice}`}>
                      <rect x="-96" y={indice * 640 / 3} width="992" height={640 / 3} />
                    </clipPath>
                  ))}
                </defs>
                <path d="M-64 213.33H864M-64 426.67H864" fill="none" stroke="var(--border)" strokeDasharray="6 10" />
                {PECAS.map((peca, indice) => (
                  <g key={peca} clipPath={`url(#${id}-recorte-${indice})`}>
                    <image
                      href="/identidade/fr-lp-0-compacto.webp"
                      width="800" height="640"
                      className="transition-transform duration-150 ease-out motion-reduce:transition-none"
                      style={{ transform: `translateX(${posicoes[indice] * 24}px)` }}
                    />
                  </g>
                ))}
              </svg>
            </div>

            <fieldset className="min-w-0 space-y-5">
              <legend className="sr-only">Posição dos fragmentos</legend>
              {PECAS.map((peca, indice) => (
                <div key={peca}>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <label htmlFor={`${id}-peca-${indice}`} className="font-medium">{peca}</label>
                    <span className={posicoes[indice] === 0 ? "text-primary" : "text-muted-foreground"} aria-hidden>
                      {posicoes[indice] === 0 ? <Check className="size-4" /> : descreverPosicao(posicoes[indice])}
                    </span>
                  </div>
                  <input
                    id={`${id}-peca-${indice}`}
                    type="range" min={-4} max={4} step={1}
                    value={posicoes[indice]}
                    aria-valuetext={descreverPosicao(posicoes[indice])}
                    onChange={(evento) => {
                      const valor = Number(evento.currentTarget.value);
                      setPosicoes((anteriores) => anteriores.map((anterior, atual) => atual === indice ? valor : anterior));
                    }}
                    className="mt-1 block h-11 w-full cursor-ew-resize accent-primary focus-visible:rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                  />
                </div>
              ))}
              <p className="text-xs leading-relaxed text-muted-foreground">
                No teclado, use as setas. O encaixe está no centro de cada trilho.
              </p>
            </fieldset>
          </div>

          <div className="mt-6 border-t border-border pt-5">
            <p role="status" aria-live="polite" aria-atomic="true" className="min-h-12 text-sm leading-relaxed">
              {resolvido ? (
                <><strong className="block font-medium text-primary">Contexto reconstruído.</strong>Você encontrou o encaixe. O segredo fica entre a gente.</>
              ) : (
                <><strong className="block font-medium">{encaixadas} de 3 peças encaixadas</strong>A fenda atravessa a marca inteira quando tudo se alinha.</>
              )}
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Button variant="outline" className="min-h-11" onClick={embaralhar}><Shuffle aria-hidden />Embaralhar</Button>
              <Dialog.Close render={<Button className="min-h-11" />}>Voltar à dashboard</Dialog.Close>
            </div>
            <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
              Só uma brincadeira. Os indicadores continuam intactos. Nada é salvo.
            </p>
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
