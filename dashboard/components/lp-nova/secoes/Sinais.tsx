import { ChevronDown, Clock3, ScanText, SlidersHorizontal } from "lucide-react";
import type { ConjuntoLeituras, Falta } from "@/lib/lp-nova/leituras";
import { ArteCompacta } from "../ArteCompacta";
import { Leituras } from "./Leituras";

export function Sinais({ conjunto }: { conjunto: ConjuntoLeituras | Falta }) {
  return (
    <section className="cena" data-cena="2" id="sinais" aria-labelledby="titulo-sinais">
      <div className="texto-cena">
        <h2 id="titulo-sinais">Sinais que você pode inspecionar.</h2>
        <p>Na mensagem, uma leitura do texto. Na conversa, contribuições dos sinais. São visões para investigar, não uma declaração do cliente.</p>
        <div className="lp-widget leituras-widget" id="metodo">
          <div className="widget-cabecalho"><span className="widget-voz voz-medido"><ScanText className="icone-lp" aria-hidden="true" />O que foi medido</span><span className="rotulo-exemplo">Leituras do sistema</span></div>
          <details className="leitura-detalhe" name="metodo-lp" open>
            <summary><ScanText className="icone-lp" aria-hidden="true" /><span>Leitura da mensagem</span><ChevronDown className="icone-lp chevron-lp" aria-hidden="true" /></summary>
            <p>Classificação textual de cada fala do cliente. Mostra uma leitura do texto, não o motivo da satisfação.</p>
          </details>
          <details className="leitura-detalhe" name="metodo-lp">
            <summary><SlidersHorizontal className="icone-lp" aria-hidden="true" /><span>Contribuição dos sinais</span><ChevronDown className="icone-lp chevron-lp" aria-hidden="true" /></summary>
            <p>Contribuições dos sinais na estimativa. Não equivalem a pontos da nota nem demonstram causa e efeito.</p>
          </details>
          <details className="leitura-detalhe" name="metodo-lp">
            <summary><Clock3 className="icone-lp" aria-hidden="true" /><span>Tempos da conversa</span><ChevronDown className="icone-lp chevron-lp" aria-hidden="true" /></summary>
            <p>Latências derivadas dos timestamps das mensagens. O treinamento do sinal de tempo usa dados sintéticos.</p>
          </details>
          <div className="widget-rodape">Inferência em CPU. Sem LLM em runtime.</div>
        </div>
        <Leituras conjunto={conjunto} />
      </div>
      <ArteCompacta etapa={2} />
    </section>
  );
}
