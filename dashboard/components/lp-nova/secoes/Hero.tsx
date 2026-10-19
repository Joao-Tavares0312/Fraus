import { FATOS_LP, formatarContador } from "@/lib/lp-nova/coreografia";
import { Palavras } from "../Palavras";

export function Hero() {
  return (
    <section id="inicio" className="cena" aria-labelledby="titulo-inicio">
      <div className="blk">
        <h1 id="titulo-inicio">
          <span className="linha"><Palavras texto="O atendimento termina." /></span>
          <span className="linha ouro"><Palavras texto="A análise começa." /></span>
        </h1>
        <p className="rv">Estime a satisfação nas conversas do seu chatbot e investigue os sinais por trás de cada resultado.</p>
        <a className="btn mag rv" href="#como-funciona" data-embaralhar>Conhecer a análise</a>
        {/* O servidor ja entrega o numero final: o contador so anima por cima. */}
        <dl className="stats rv">
          {FATOS_LP.map(({ valor, rotulo }) => (
            <div className="stat" key={rotulo}><dd data-n={valor}>{formatarContador(valor, 2)}</dd><dt>{rotulo}</dt></div>
          ))}
        </dl>
      </div>
    </section>
  );
}
