import type { Metadata } from "next";
import "./lp.css";
import { CenaLeitura } from "@/components/lp-nova/CenaLeitura";
import { Analista } from "@/components/lp-nova/secoes/Analista";
import { Fecho } from "@/components/lp-nova/secoes/Fecho";
import { Hero } from "@/components/lp-nova/secoes/Hero";
import { Limites } from "@/components/lp-nova/secoes/Limites";
import { Problema } from "@/components/lp-nova/secoes/Problema";
import { Sinais } from "@/components/lp-nova/secoes/Sinais";
import { Topo } from "@/components/lp-nova/secoes/Topo";
import { carregarLeituras } from "@/lib/lp-nova/carregar";

export const metadata: Metadata = {
  title: "Fraus — contexto, não certeza",
  description:
    "O Fraus estima satisfação em atendimentos de chatbot, sem pesquisa e sem LLM em runtime. Conheça o método e seus limites.",
};

/** Conteudo publico SSR; snapshots so entram quando validados pelo servidor. */
export default async function PaginaInicial() {
  const conjunto = await carregarLeituras();
  return (
    <div className="lp">
      <a className="lp-pular" href="#inicio">Ir para o conteúdo</a>
      <Topo />
      <main>
        <CenaLeitura>
          <Hero />
          <Problema />
          <Sinais conjunto={conjunto} />
          <Analista />
        </CenaLeitura>
        <Limites />
      </main>
      <Fecho />
    </div>
  );
}
