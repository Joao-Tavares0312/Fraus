import Link from "next/link";

export function Fecho() {
  return (
    <>
      <section data-marco="fecho" aria-labelledby="titulo-fecho" className="ln-sec ln-fecho">
        <div className="ln-wrap">
          <div className="ln-coluna">
          <h2 id="titulo-fecho" className="display-vitrine ln-fecho__titulo">
            Leia o que ficou nas <span className="ln-dito">entrelinhas.</span>
          </h2>
          <div className="ln-botoes">
            <Link href="/entrar" className="ln-botao ln-botao--feixe">
              Entrar no Fraus
            </Link>
            <Link href="/cadastrar" className="ln-botao ln-botao--contorno">
              Tenho um convite
            </Link>
          </div>
          </div>
        </div>
      </section>
      <footer className="ln-rodape">
        <div className="ln-wrap ln-rodape__faixa">
          <span>Conversas sintéticas, lidas pelo motor real</span>
          <span>NPS estimado</span>
          <span>Sem LLM em runtime</span>
          <Link href="/">Vitrine anterior</Link>
        </div>
      </footer>
    </>
  );
}
