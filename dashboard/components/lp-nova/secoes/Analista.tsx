import Link from "next/link";
import { ArrowRight, ChartNoAxesCombined, ListFilter, MessagesSquare } from "lucide-react";
import { ArteCompacta } from "../ArteCompacta";

export function Analista() {
  return (
    <section className="cena" data-cena="3" id="na-pratica" aria-labelledby="titulo-percurso">
      <div className="texto-cena">
        <h2 id="titulo-percurso">Do panorama ao atendimento.</h2>
        <p>Compare satisfação estimada e tempo de resposta. Depois, encontre os atendimentos e volte às mensagens que sustentam a leitura.</p>
        <ol className="fluxo-lp" aria-label="Percurso de investigação na ferramenta">
          <li><span className="fluxo-icone"><ChartNoAxesCombined className="icone-lp" aria-hidden="true" /></span><div><h3>Compare o panorama</h3><p>NPS inferido e latência, juntos.</p></div></li>
          <li><span className="fluxo-icone"><ListFilter className="icone-lp" aria-hidden="true" /></span><div><h3>Recorte os atendimentos</h3><p>Use o período para localizar os casos.</p></div></li>
          <li><span className="fluxo-icone"><MessagesSquare className="icone-lp" aria-hidden="true" /></span><div><h3>Volte à conversa</h3><p>Confira a transcrição e os sinais.</p></div></li>
        </ol>
        <Link className="acao-lp secundaria" href="/dashboard" prefetch={false}>Abrir a dashboard<ArrowRight className="icone-lp" aria-hidden="true" /></Link>
      </div>
      <ArteCompacta etapa={3} />
    </section>
  );
}
