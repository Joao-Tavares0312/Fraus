import Link from "next/link";
import { IconeDeAcao } from "@/components/IconeDeAcao";

export function Fecho() {
  return (
    <>
      <section data-marco="fecho" aria-labelledby="titulo-fecho" className="ln-sec ln-fecho">
        <div className="ln-wrap">
          <div className="ln-coluna">
            <h2 id="titulo-fecho" className="display-vitrine ln-fecho__titulo">
              Traga o contexto para a sua análise.
            </h2>
            <div className="ln-botoes">
              <Link href="/entrar" className="ln-botao ln-botao--ouro">
                <IconeDeAcao acao="entrar" />
                Entrar no Fraus
              </Link>
              <Link href="/cadastrar" className="ln-botao ln-botao--contorno">
                <IconeDeAcao acao="criar" />
                Criar conta
              </Link>
            </div>
            <p className="ln-prosa">
              Analise conversas e confira os sinais antes de tirar conclusões.
            </p>
          </div>
        </div>
      </section>
      <footer className="ln-rodape">
        <div className="ln-wrap ln-rodape__faixa">
          <span>Casos ilustrativos · conversas sintéticas</span>
          <span>NPS estimado</span>
          <span>Sem LLM em runtime</span>
        </div>
      </footer>
    </>
  );
}
