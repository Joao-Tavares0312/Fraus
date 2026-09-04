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
 * TRES DESLIGAMENTOS, nao dois. `prefers-reduced-motion` e o obvio. O
 * segundo, corrigido em 04/09/2026: a ROTA. O `Atelier` mora no layout raiz e
 * e compartilhado por toda a ferramenta, mas a coreografia so vale na
 * vitrine (`lib/cena.ts`, `coreografiaValeEm`) -- fora dela o parametro
 * `ativo` chega `false` e a funcao nem registra o listener de scroll.
 * Desligado precisa ser DESLIGADO, nao "escutando e ignorando": um listener
 * vivo que descarta o valor ainda succiona um evento por quadro de rolagem
 * de uma tela que o analista le por horas. O terceiro e o mesmo de sempre:
 * quem pede menos movimento nao recebe uma versao lenta, recebe a cena
 * PARADA no estado inicial -- a mesma decisao da secao 8.7 sobre o campo de
 * particulas, que devolve `null` em vez de girar devagar.
 *
 * NOS TRES CASOS de desligamento (rota fora da vitrine, reduced-motion, ou
 * os dois) o destino e o MESMO: `aplicar(0)`, o estado inicial, onde os tres
 * fatores valem 1 -- exatamente a cena de hoje, parada.
 *
 * O QUE ISTO ESCREVE E FATOR, NAO OPACIDADE: `intensidadeDaCamada` devolve um
 * numero de 0 a 1 que o CSS multiplica pelo token de opacidade do tema
 * (`--grade-op`, `--sol-op`, `--estrelas-op`) em `Atelier.tsx`. O fallback la
 * e 1, nao o valor de hoje -- assim a primeira pintura, antes deste hook
 * montar, mostra a cena exatamente como ela e hoje.
 */
export function useProgressoDaCena(ativo: boolean): void {
  useEffect(() => {
    const raiz = document.documentElement;

    function aplicar(progresso: number) {
      for (const camada of CAMADAS) {
        raiz.style.setProperty(
          `--cena-${camada}`,
          String(intensidadeDaCamada(camada, progresso)),
        );
      }
    }

    if (!ativo) {
      aplicar(0);
      return;
    }

    const consulta = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (consulta.matches) {
      aplicar(0);
      return;
    }

    // `agendado` guarda o id do rAF pendente, no mesmo desenho do
    // `useEspecular`: sem isto o cleanup so removeria o listener de scroll,
    // e um frame ja enfileirado ainda rodaria depois da desmontagem,
    // escrevendo na raiz por um componente que nao existe mais.
    let agendado = 0;
    let pendente = false;
    function aoRolar() {
      if (pendente) return;
      pendente = true;
      agendado = requestAnimationFrame(() => {
        agendado = 0;
        pendente = false;
        const rolavel = document.body.scrollHeight - window.innerHeight;
        aplicar(rolavel > 0 ? window.scrollY / rolavel : 0);
      });
    }

    aoRolar();
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => {
      if (agendado) cancelAnimationFrame(agendado);
      agendado = 0;
      window.removeEventListener("scroll", aoRolar);
    };
    // `ativo` na dependencia: o `Atelier` e uma unica instancia no layout
    // raiz, sobrevive a navegacao client-side entre rotas, e `usePathname`
    // muda sem remontar o componente. Sem `ativo` aqui o efeito rodaria uma
    // vez com o valor da PRIMEIRA rota visitada e nunca mais -- sair da LP
    // para o Operate deixaria o listener de scroll vivo, o exato defeito que
    // esta correcao existe para fechar.
  }, [ativo]);
}
