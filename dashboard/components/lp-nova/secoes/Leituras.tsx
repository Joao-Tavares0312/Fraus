import type { ConjuntoLeituras, Falta } from "@/lib/lp-nova/leituras";
import { SeletorDeLeituras } from "../SeletorDeLeituras";

export function Leituras({ conjunto }: { conjunto: ConjuntoLeituras | Falta }) {
  return (
    <section id="leituras" data-marco="leitura" aria-labelledby="titulo-leituras" className="ln-sec ln-leituras">
      <div className="ln-wrap">
        <h2 id="titulo-leituras" className="titulo-vitrine ln-leituras__titulo">
          Escolha uma conversa. Veja o Fraus ler.
        </h2>
        {"falta" in conjunto ? (
          <p className="ln-vazio" role="status">
            {conjunto.falta}.
          </p>
        ) : (
          <SeletorDeLeituras conjunto={conjunto} />
        )}
      </div>
    </section>
  );
}
