import type { Metadata } from "next";
import "./leitura.css";
import { CenaLeitura } from "@/components/lp-nova/CenaLeitura";
import { Analista } from "@/components/lp-nova/secoes/Analista";
import { Fecho } from "@/components/lp-nova/secoes/Fecho";
import { Fusor } from "@/components/lp-nova/secoes/Fusor";
import { Hero } from "@/components/lp-nova/secoes/Hero";
import { Leituras } from "@/components/lp-nova/secoes/Leituras";
import { Limites } from "@/components/lp-nova/secoes/Limites";
import { Problema } from "@/components/lp-nova/secoes/Problema";
import { Topo } from "@/components/lp-nova/secoes/Topo";
import { carregarLeituras } from "@/lib/lp-nova/carregar";

export const metadata: Metadata = {
  title: "Fraus — leia o que ficou nas entrelinhas",
  description:
    "O Fraus mede a satisfação em atendimentos de chatbot sem perguntar nada ao cliente. Veja o motor ler cinco conversas.",
};

/**
 * A LP NOVA (`/leitura`): experimento com vgpu, ao lado da vitrine de `/`.
 * Secoes em Server Components; so a cena e o seletor sao de cliente.
 */
export default async function PaginaLeitura() {
  const conjunto = await carregarLeituras();
  const obrigado = "leituras" in conjunto ? (conjunto.leituras.find((l) => l.id === "obrigado") ?? null) : null;
  return (
    <CenaLeitura>
      <Topo />
      <main>
        <Hero leitura={obrigado} />
        <Problema />
        <Fusor />
        <Leituras conjunto={conjunto} />
        <Analista />
        <Limites />
        <Fecho />
      </main>
    </CenaLeitura>
  );
}
