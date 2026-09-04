"use client";

import { useEffect } from "react";
import { intensidadeDaCamada, type Camada } from "@/lib/cena";

const CAMADAS: Camada[] = ["grade", "planeta", "estrelas"];

/**
 * Liga a rolagem as variaveis da cena.
 *
 * SEM useState, de proposito: um setState por evento de rolagem re-renderiza a
 * arvore a cada quadro, atras de tabela e grafico. Escreve direto no no dentro
 * de rAF, como o `useEspecular` ja faz.
 *
 * DOIS DESLIGAMENTOS. `prefers-reduced-motion` e o obvio; o segundo e o
 * esquecido: quem pede menos movimento nao recebe uma versao lenta, recebe a
 * cena PARADA no estado inicial -- a mesma decisao da secao 8.7 sobre o campo
 * de particulas, que devolve `null` em vez de girar devagar.
 *
 * O QUE ISTO ESCREVE E FATOR, NAO OPACIDADE: `intensidadeDaCamada` devolve um
 * numero de 0 a 1 que o CSS multiplica pelo token de opacidade do tema
 * (`--grade-op`, `--sol-op`, `--estrelas-op`) em `Atelier.tsx`. O fallback la
 * e 1, nao o valor de hoje -- assim a primeira pintura, antes deste hook
 * montar, mostra a cena exatamente como ela e hoje.
 */
export function useProgressoDaCena(): void {
  useEffect(() => {
    const raiz = document.documentElement;
    const consulta = window.matchMedia("(prefers-reduced-motion: reduce)");

    function aplicar(progresso: number) {
      for (const camada of CAMADAS) {
        raiz.style.setProperty(
          `--cena-${camada}`,
          String(intensidadeDaCamada(camada, progresso)),
        );
      }
    }

    if (consulta.matches) {
      aplicar(0);
      return;
    }

    let pendente = false;
    function aoRolar() {
      if (pendente) return;
      pendente = true;
      requestAnimationFrame(() => {
        pendente = false;
        const rolavel = document.body.scrollHeight - window.innerHeight;
        aplicar(rolavel > 0 ? window.scrollY / rolavel : 0);
      });
    }

    aoRolar();
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => window.removeEventListener("scroll", aoRolar);
  }, []);
}
