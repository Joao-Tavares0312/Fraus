import Link from "next/link";
import { Palavras } from "../Palavras";

export function Fecho() {
  return (
    <section id="fecho" className="cena c" aria-labelledby="titulo-fecho">
      <div className="blk">
        <h2 id="titulo-fecho"><Palavras texto="Leia o que ficou nas entrelinhas." /></h2>
        <p className="rv">Contexto, não certeza.</p>
        <div className="acoes rv">
          <Link className="btn mag" href="/entrar" prefetch={false} data-embaralhar>Entrar no Fraus</Link>
          <Link className="btn o mag" href="/cadastrar" prefetch={false} data-embaralhar>Criar conta</Link>
        </div>
      </div>
    </section>
  );
}

/** Os contadores do topo sao fatos do motor; o que e inferido e a nota. */
export function Rodape() {
  return <footer className="rodape-lp">Modelos locais · sem LLM em runtime · toda nota é inferida, nunca declarada</footer>;
}
