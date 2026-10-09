import type { Metadata } from "next";
import "./lp.css";
import { CenaLeitura } from "@/components/lp-nova/CenaLeitura";
import { Analista } from "@/components/lp-nova/secoes/Analista";
import { Fecho } from "@/components/lp-nova/secoes/Fecho";
import { Hero } from "@/components/lp-nova/secoes/Hero";
import { Leituras } from "@/components/lp-nova/secoes/Leituras";
import { Limites } from "@/components/lp-nova/secoes/Limites";
import { Mascara } from "@/components/lp-nova/secoes/Mascara";
import { Problema } from "@/components/lp-nova/secoes/Problema";
import { Topo } from "@/components/lp-nova/secoes/Topo";
import { carregarLeituras } from "@/lib/lp-nova/carregar";

export const metadata: Metadata = {
  title: "Fraus — leia o que ficou nas entrelinhas",
  description:
    "O Fraus mede a satisfação em atendimentos de chatbot sem perguntar nada ao cliente. Veja o motor ler cinco conversas.",
};

/**
 * A LP (rota `/`, desde 09/10/2026): a mistura da LP nova com a vitrine
 * antiga, toda em vgpu. Da nova: hero em particulas, leituras gravadas e as
 * secoes de texto. Da antiga: o fosforo de osciloscopio, o orbe de tres
 * manchas e a mascara que vira constelacao. Secoes em Server Components; so a
 * cena e o seletor sao de cliente. `/leitura`, onde ela nasceu, redireciona
 * para ca (`next.config.ts`).
 */
export default async function PaginaInicial() {
  const conjunto = await carregarLeituras();
  const obrigado = "leituras" in conjunto ? (conjunto.leituras.find((l) => l.id === "obrigado") ?? null) : null;
  return (
    <CenaLeitura>
      <Topo />
      <main>
        <Hero leitura={obrigado} />
        <Problema />
        <Mascara leitura={obrigado} />
        <Leituras conjunto={conjunto} />
        <Analista />
        <Limites />
        <Fecho />
      </main>
    </CenaLeitura>
  );
}
