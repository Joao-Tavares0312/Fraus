import { ArrowRight } from "lucide-react";
import { ArteCompacta } from "../ArteCompacta";

export function Hero() {
  return (
    <section className="cena hero" data-cena="0" id="inicio" aria-labelledby="titulo-inicio">
      <div className="texto-cena">
        <h1 id="titulo-inicio"><span>O atendimento<br />termina.</span><span className="titulo-abertura">A análise começa.</span></h1>
        <p>Estime a satisfação nas conversas do seu chatbot e investigue os sinais por trás de cada resultado.</p>
        <a className="acao-lp" href="#como-funciona">Conhecer a análise<ArrowRight className="icone-lp" aria-hidden="true" /></a>
      </div>
      <ArteCompacta etapa={0} />
    </section>
  );
}
