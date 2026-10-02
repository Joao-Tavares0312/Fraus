import Link from "next/link";

/**
 * O FECHO: a tese que o nome carrega. Fraus e a divindade romana da fraude;
 * o cliente mente por cortesia, o texto entrega. O "o texto nao" vai em
 * ambar porque e sobre o dito -- e o orbe, atras, volta a pender para o ambar.
 */
export function Fecho() {
  return (
    <section id="fecho" aria-labelledby="titulo-fecho" className="vt-fecho">
      <div className="vt-wrap">
        <h2 id="titulo-fecho" className="display-vitrine vt-fecho__titulo">
          O cliente mente. <span className="vt-dito">O texto não.</span>
        </h2>
        <p className="vt-prosa vt-fecho__prosa">
          NPS inferido do texto, sempre com a etiqueta de estimativa. Onde falta
          dado, a tela diz o que falta.
        </p>
        <div className="vt-botoes">
          <Link href="/entrar" className="vt-botao vt-botao--feixe">
            Iniciar leitura →
          </Link>
          <Link href="/cadastrar" className="vt-botao vt-botao--contorno">
            Criar acesso
          </Link>
        </div>
      </div>
    </section>
  );
}

export function Rodape() {
  return (
    <footer className="vt-rodape">
      <div className="vt-wrap">
        <span className="vt-rotulo">Fraus · trabalho acadêmico · modelos locais, sem LLM em runtime</span>
        <span className="vt-rotulo">reconhece emoção no texto · não pontua atendentes</span>
      </div>
    </footer>
  );
}
