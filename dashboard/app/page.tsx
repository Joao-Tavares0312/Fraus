import "./vitrine.css";
import { CabecalhoVitrine } from "@/components/lp/CabecalhoVitrine";
import { CenaVitrine } from "@/components/lp/CenaVitrine";
import { Constelacao } from "@/components/lp/Constelacao";
import { Fecho, Rodape } from "@/components/lp/Fecho";
import { Hero } from "@/components/lp/Hero";
import { SemSinal } from "@/components/lp/SemSinal";
import { Sistema } from "@/components/lp/Sistema";

/**
 * A VITRINE (rota `/`) -- modo Persuade, a unica superficie onde a expressao
 * pode ser alta. Direcao aprovada em 01/10/2026 sobre a mescla de prototipos:
 * hero e orbe da v0, fosforo de osciloscopio da v1, mascara da v6 virando a
 * constelacao da v4, e o orbe atravessando a pagina como fusor.
 *
 * As secoes sao Server Components; so a `CenaVitrine` (canvas + motor) e de
 * cliente. Toda amostra de conversa e nota e SINTETICA e diz isso onde
 * aparece; os numeros-fato vem de `components/lp/fatos.ts`.
 */
export default function PaginaInicial() {
  return (
    <CenaVitrine>
      <CabecalhoVitrine />
      <main>
        <Hero />
        <Constelacao />
        <SemSinal />
        <Sistema />
        <Fecho />
      </main>
      <Rodape />
    </CenaVitrine>
  );
}
