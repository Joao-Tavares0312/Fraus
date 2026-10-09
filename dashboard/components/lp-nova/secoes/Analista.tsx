import { SegmentoLED } from "@/components/instrumento/SegmentoLED";

/**
 * PARA QUEM OPERA: tres garantias, cada uma com a peca REAL que a cumpre na
 * ferramenta. O LED apagado e o "sem sinal" de verdade, nao ilustracao.
 */
export function Analista() {
  return (
    <section data-marco="recuo" aria-labelledby="titulo-analista" className="ln-sec ln-analista">
      <div className="ln-wrap">
        <h2 id="titulo-analista" className="titulo-vitrine">
          Feito para quem precisa confiar no número antes de agir.
        </h2>
        <ul className="ln-garantias">
          <li>
            <span className="ln-garantias__peca" aria-hidden>
              <span className="ln-regua">
                <span className="ln-regua__dito">dito</span>
                <span className="ln-regua__medido">medido</span>
              </span>
            </span>
            <h3>O NPS é inferido, e diz isso.</h3>
            <p>
              Todo indicador carrega a etiqueta de estimativa e um intervalo. Com menos de 30 atendimentos com sinal, o
              ponto some e fica só o intervalo: amostra pequena não vira certeza.
            </p>
          </li>
          <li>
            <span className="ln-garantias__peca">
              <SegmentoLED valor={null} rotulo="nota" altura={40} cor="medido" traco="fino" celulas={2} />
            </span>
            <h3>Sem sinal nunca vira zero.</h3>
            <p>
              Conversa sem fala do cliente não tem nota, não entra em média e não aparece como insatisfeita. O display
              fica ligado e apagado, do jeito que você viu na leitura sem sinal.
            </p>
          </li>
          <li>
            <span className="ln-garantias__peca" aria-hidden>
              <span className="ln-marcada">não quero segunda via</span>
            </span>
            <h3>Cada nota aponta a fala que a puxou.</h3>
            <p>
              O classificador lê mensagem por mensagem. Em vez de um número opaco, a transcrição mostra quais falas
              derrubaram a nota, com a probabilidade de cada uma.
            </p>
          </li>
        </ul>
      </div>
    </section>
  );
}
