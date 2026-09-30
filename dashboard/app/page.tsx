import "./vitrine.css";
import { CabecalhoVitrine } from "@/components/lp/CabecalhoVitrine";
import { Fecho, Rodape } from "@/components/lp/Fecho";
import { Hero } from "@/components/lp/Hero";
import { Leitura } from "@/components/lp/Leitura";
import { Metodo } from "@/components/lp/Metodo";
import { Sistema } from "@/components/lp/Sistema";

/**
 * A VITRINE (rota `/`) -- modo Persuade, e a unica superficie do produto onde a
 * expressao pode ser alta. O Instrumento (spec 2026-09-30): telemetria e
 * hairline da Regua, numeros em LED do Segmento e o hero de orbe da Aurora.
 *
 * Server Component: a pagina inteira e estatica. So `Revelar` (o reveal por
 * rolagem) e `MarcaFraus` (o gesto dos cinco cliques) sao de cliente.
 *
 * Toda amostra de conversa e nota e SINTETICA e diz isso onde aparece; os
 * numeros-fato (07 familias, 39 features, 03 BERTimbau, 00 LLMs) sao os do
 * CLAUDE.md. Nao ha depoimento, cliente nem metrica de uso inventados.
 */
export default function PaginaInicial() {
  return (
    <div className="vt">
      <CabecalhoVitrine />
      <main>
        <Hero />
        <Leitura />
        <Sistema />
        <Metodo />
        <Fecho />
      </main>
      <Rodape />
    </div>
  );
}
