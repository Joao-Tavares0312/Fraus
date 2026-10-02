import { SegmentoLED } from "@/components/instrumento/SegmentoLED";

/**
 * O "SEM SINAL" -- a invariante 2 do CLAUDE.md como cena.
 *
 * O orbe chega aqui cinza e parado, e um aglomerado de pontos orbita sem
 * nunca cair nele (`data-vt="ancora-vazio"` diz ao motor onde). O display fica
 * apagado com os segmentos desenhados: o medidor esta ligado e nao leu nada.
 * Nunca zero.
 */
export function SemSinal() {
  return (
    <section id="vazio" aria-labelledby="titulo-vazio" className="vt-sec">
      <div className="vt-wrap vt-vazio">
        <div>
          <h2 id="titulo-vazio" className="titulo-vitrine">
            Ausência de dado não é insatisfação.
          </h2>
          <p className="vt-prosa vt-vazio__prosa">
            Quando o cliente não escreve nada, o medidor continua ligado — só não
            leu nada. O Fraus mostra o display apagado e escreve “sem sinal”, em
            vez de devolver um zero que puxaria a média para baixo.
          </p>
          <div className="vt-medidor">
            <SegmentoLED
              valor={null}
              rotulo="nota do atendimento sem fala do cliente"
              altura={72}
              cor="tinta"
              traco="fino"
            />
            <span className="vt-rotulo">○ sem sinal · não é zero</span>
          </div>
          <ul className="vt-citacoes" aria-label="Transcrição sintética sem fala do cliente">
            <li><span className="vt-rotulo">atendimento a-0107 · amostra sintética</span></li>
            <li><span className="vt-rotulo">atendente virtual · 09:14</span>Olá! Como posso ajudar?</li>
            <li><span className="vt-rotulo">atendente virtual · 09:19</span>Ainda está por aí?</li>
            <li><span className="vt-rotulo">atendente virtual · 09:24</span>Encerrando o atendimento por inatividade.</li>
            <li className="vt-citacoes__falta">falta: ao menos uma fala do cliente</li>
          </ul>
        </div>
        <div aria-hidden className="vt-ancora" data-vt="ancora-vazio" />
      </div>
    </section>
  );
}
