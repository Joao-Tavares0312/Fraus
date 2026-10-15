import type { ConjuntoLeituras, Falta } from "@/lib/lp-nova/leituras";
import { SeletorDeLeituras } from "../SeletorDeLeituras";

export function Leituras({ conjunto }: { conjunto: ConjuntoLeituras | Falta }) {
  if ("falta" in conjunto) {
    return (
      <aside id="leituras" data-marco="leitura" aria-label="Disponibilidade das leituras" className="ln-leituras ln-leituras--ausentes">
        <div className="ln-wrap">
          <p className="ln-vazio" role="status">
            <strong>Leituras gravadas indisponíveis.</strong> {conjunto.falta}.
            {" "}O caso acima é um roteiro sintético, sem resultado publicado.{" "}
            <a href="#limites">Conheça os limites da estimativa.</a>
          </p>
        </div>
      </aside>
    );
  }
  return (
    <section id="leituras" data-marco="leitura" aria-labelledby="titulo-leituras" className="ln-sec ln-leituras">
      <div className="ln-wrap">
        <h2 id="titulo-leituras" className="titulo-vitrine ln-leituras__titulo">
          Escolha uma conversa. Inspecione a leitura.
        </h2>
        <SeletorDeLeituras conjunto={conjunto} />
      </div>
    </section>
  );
}
