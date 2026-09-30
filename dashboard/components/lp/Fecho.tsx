import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Revelar } from "./Revelar";

/**
 * O FECHO e o RODAPE. A manchete do fecho e a frase da vitrine anterior -- "o
 * que foi dito nao e tudo que foi sentido" --, com o encoding de sempre: o
 * dito em ambar, o sentido em azul. O hero abre com "entrelinhas"; este fecho
 * devolve a tese que o nome da marca carrega (o cliente mente, o texto nao).
 */
export function Fecho() {
  return (
    <section aria-labelledby="titulo-fecho" className="vt-sec vt-fecho">
      <Revelar className="vt-wrap">
        <p className="vt-rotulo justify-center">a conversa já tem a resposta</p>
        <h2
          id="titulo-fecho"
          className="display-vitrine mx-auto mt-8 max-w-[14ch]"
        >
          O que foi <span className="text-dito-texto">dito</span> não é tudo que
          foi <span className="text-medido-texto">sentido.</span>
        </h2>
        <p className="vt-prosa mx-auto mt-8 text-lg">
          Transforme atendimentos em evidência operacional sem perguntar ao
          cliente o que ele já demonstrou.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <Link href="/entrar" className="vt-botao vt-botao--ouro">
            Entrar <ArrowRight aria-hidden />
          </Link>
          <Link href="/cadastrar" className="vt-botao vt-botao--contorno">
            Criar acesso
          </Link>
        </div>
      </Revelar>
    </section>
  );
}

export function Rodape() {
  return (
    <footer className="vt-rodape">
      <div className="vt-wrap">
        <span>Fraus · análise de satisfação em português</span>
        <span>modelos locais · sem LLM em runtime</span>
      </div>
    </footer>
  );
}
