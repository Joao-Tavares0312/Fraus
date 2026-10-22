import type { Metadata } from "next";
import localFont from "next/font/local";
import "./lp.css";
import { Ceu } from "@/components/lp-nova/Ceu";
import { Coreografia } from "@/components/lp-nova/Coreografia";
import { Analista } from "@/components/lp-nova/secoes/Analista";
import { Faixa, Letreiro } from "@/components/lp-nova/secoes/Faixa";
import { Fecho, Rodape } from "@/components/lp-nova/secoes/Fecho";
import { Hero } from "@/components/lp-nova/secoes/Hero";
import { Limites } from "@/components/lp-nova/secoes/Limites";
import { Problema } from "@/components/lp-nova/secoes/Problema";
import { Sinais } from "@/components/lp-nova/secoes/Sinais";
import { Topo } from "@/components/lp-nova/secoes/Topo";
import { carregarLeituras } from "@/lib/lp-nova/carregar";

// Fontes variaveis locais e so desta rota: a dashboard nao baixa nenhuma delas.
const display = localFont({ src: "../public/identidade/unbounded-variavel.woff2", weight: "500 700", variable: "--fonte-display", display: "swap", fallback: ["system-ui", "sans-serif"] });
const corpo = localFont({ src: "../public/identidade/space-grotesk-variavel.woff2", weight: "400 500", variable: "--fonte-corpo", display: "swap", fallback: ["system-ui", "sans-serif"] });

export const metadata: Metadata = {
  title: "Fraus — contexto, não certeza",
  description:
    "O Fraus estima satisfação em atendimentos de chatbot, sem pesquisa e sem LLM em runtime. Conheça o método e seus limites.",
};

/** Conteudo publico SSR; a coreografia so anima o que ja chegou pronto. */
export default async function PaginaInicial() {
  const conjunto = await carregarLeituras();
  return (
    <div className={`lp ${display.variable} ${corpo.variable}`}>
      <Ceu />
      <noscript><style>{".lp-pre{display:none}"}</style></noscript>
      <div className="lp-pre" aria-hidden="true"><small>Fraus<br />Contexto, não certeza.</small><b data-pre-contador>000</b></div>
      <a className="lp-pular" href="#inicio">Ir para o conteúdo</a>
      <Coreografia />
      <Topo />
      <main>
        <Hero />
        <Letreiro />
        <Problema />
        <Sinais conjunto={conjunto} />
        <Faixa />
        <Analista />
        <Limites />
        <Fecho />
      </main>
      <Rodape />
    </div>
  );
}
