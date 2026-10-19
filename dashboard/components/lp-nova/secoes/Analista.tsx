import Link from "next/link";
import { Palavras } from "../Palavras";

const PASSOS = [
  { titulo: "Compare o panorama", texto: "NPS inferido e latência, juntos." },
  { titulo: "Recorte os atendimentos", texto: "Use o período para localizar os casos." },
  { titulo: "Volte à conversa", texto: "Confira a transcrição e os sinais." },
];

export function Analista() {
  return (
    <section id="na-pratica" className="cena r" aria-labelledby="titulo-percurso">
      <div className="blk">
        <h2 id="titulo-percurso"><Palavras texto="Do panorama ao atendimento." /></h2>
        <div className="steps">
          <span className="stepline" aria-hidden="true" data-passos />
          <ol aria-label="Percurso de investigação na ferramenta">
            {PASSOS.map(({ titulo, texto }) => <li className="step" key={titulo}><h3>{titulo}</h3><p>{texto}</p></li>)}
          </ol>
        </div>
        <Link className="btn mag rv" href="/dashboard" prefetch={false} data-embaralhar>Abrir a dashboard</Link>
      </div>
    </section>
  );
}
