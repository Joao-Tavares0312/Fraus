import type { ConjuntoLeituras, Falta } from "@/lib/lp-nova/leituras";
import { Palavras } from "../Palavras";
import { Leituras } from "./Leituras";

const CARTOES = [
  { titulo: "Leitura da mensagem", texto: "Classificação textual de cada fala do cliente. Uma leitura do texto, não o motivo da satisfação." },
  { titulo: "Contribuição dos sinais", texto: "Contribuições na estimativa. Não equivalem a pontos da nota nem a causa e efeito." },
  { titulo: "Tempos da conversa", texto: "Latências derivadas dos timestamps das mensagens." },
];

export function Sinais({ conjunto }: { conjunto: ConjuntoLeituras | Falta }) {
  return (
    <section id="sinais" className="cena" aria-labelledby="titulo-sinais">
      <div className="blk">
        <h2 id="titulo-sinais"><Palavras texto="Sinais que você pode inspecionar." /></h2>
        <span className="tag chanfro m rv" data-embaralhar>Leituras do sistema · medido</span>
        {CARTOES.map(({ titulo, texto }) => (
          <div className="card placas fio rv" key={titulo}><h3>{titulo}</h3><p>{texto}</p></div>
        ))}
        <div className="ruler" aria-hidden="true"><i data-regua /></div>
        <p className="nota-lp">Inferência em CPU. Sem LLM em runtime.</p>
        <Leituras conjunto={conjunto} />
      </div>
    </section>
  );
}
