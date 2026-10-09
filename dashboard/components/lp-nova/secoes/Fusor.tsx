import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { FAMILIAS_DO_VETOR, FATOS_DO_MODELO, emDuasCasas } from "@/components/lp/fatos";

/**
 * O FUSOR: a secao alta. O texto fica preso (sticky) enquanto a cena junta as
 * particulas em sete enxames -- do tamanho REAL de cada familia -- e as joga
 * no orbe. Dois marcos: o enxame no inicio da secao, o orbe no meio.
 */
export function Fusor() {
  return (
    <section aria-labelledby="titulo-fusor" className="ln-sec ln-fusor">
      <span data-marco="enxame" className="ln-marco" aria-hidden />
      <span data-marco="orbe" className="ln-marco ln-marco--meio" aria-hidden />
      <div className="ln-wrap ln-fusor__preso">
        <div className="ln-coluna">
          <h2 id="titulo-fusor" className="titulo-vitrine">
            Sete famílias leem a mesma conversa.
          </h2>
          <p className="ln-prosa">
            Cada partícula ali é parte de um sinal. O tamanho de cada enxame é a contagem real de features da família:{" "}
            {FATOS_DO_MODELO.features} no total, fundidas num modelo só. Ao atravessar o fusor, o que foi dito vira
            medido, de âmbar para azul.
          </p>
          <ul className="ln-familias">
            {FAMILIAS_DO_VETOR.map((f) => (
              <li key={f.chave}>
                <SegmentoLED valor={emDuasCasas(f.qtd)} rotulo={`features de ${f.rotulo}`} altura={22} cor="tinta" traco="fino" />
                <span className="ln-familias__nome">{f.rotulo}</span>
                <span className="ln-familias__leitura">{f.leitura}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
