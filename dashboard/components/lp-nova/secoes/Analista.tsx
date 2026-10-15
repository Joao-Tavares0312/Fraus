import { SegmentoLED } from "@/components/instrumento/SegmentoLED";

/**
 * PARA QUEM OPERA: limites de leitura, ligados as pecas reais da ferramenta.
 * O LED apagado e o "sem sinal" de verdade, nao ilustracao.
 */
export function Analista() {
  return (
    <section data-marco="recuo" aria-labelledby="titulo-analista" className="ln-sec ln-analista">
      <div className="ln-wrap">
        <h2 id="titulo-analista" className="titulo-vitrine">
          Do panorama ao atendimento que merece atenção.
        </h2>
        <ul className="ln-garantias">
          <li>
            <span className="ln-garantias__peca" aria-hidden>
              <span className="ln-regua">
                <span className="ln-regua__dito">dito</span>
                <span className="ln-regua__medido">medido</span>
              </span>
            </span>
            <h3>Encontre o que precisa ser revisto.</h3>
            <p>
              Filtre atendimentos por período e categoria e acompanhe o NPS estimado junto à latência observada.
              Desça do panorama para a conversa: contenção não é prova de resolução.
            </p>
          </li>
          <li>
            <span className="ln-garantias__peca">
              <SegmentoLED valor={null} rotulo="nota" altura={40} cor="medido" traco="fino" celulas={2} />
            </span>
            <h3>Separe ausência de insatisfação.</h3>
            <p>
              Conversa sem fala do cliente fica sem sinal: não tem nota, não entra em média e não vira zero.
              Você vê o que falta antes de comparar resultados.
            </p>
          </li>
          <li>
            <span className="ln-garantias__peca" aria-hidden>
              <span className="ln-marcada">não quero segunda via</span>
            </span>
            <h3>Confira a leitura na transcrição.</h3>
            <p>
              Consulte as probabilidades do classificador de texto por mensagem e as contribuições dos sinais no fusor.
              A inclinação de uma fala não explica sozinha a nota da conversa.
            </p>
          </li>
        </ul>
      </div>
    </section>
  );
}
