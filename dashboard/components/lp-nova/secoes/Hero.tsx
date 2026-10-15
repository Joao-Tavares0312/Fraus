import Link from "next/link";
import { IconeDeAcao } from "@/components/IconeDeAcao";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import type { Leitura } from "@/lib/lp-nova/leituras";

/**
 * A fala e o caso sao sinteticos; a nota so aparece se foi gravada pelo motor.
 * A fala fica no DOM; na cena viva, as particulas ocupam os mesmos pixels.
 */
export function Hero({ leitura }: { leitura: Leitura | null }) {
  return (
    <section id="topo" data-marco="frase" aria-labelledby="titulo-ln" className="ln-hero">
      <div className="ln-wrap ln-hero__miolo">
        <h1 id="titulo-ln" className="display-vitrine ln-hero__titulo">
          Um obrigado <span className="ln-medido">não conta tudo.</span>
        </h1>

        <figure className="ln-fala">
          <blockquote>
            <p data-ln="frase" className="ln-fala__texto">
              ok, obrigado 🙂
            </p>
          </blockquote>
          <figcaption className="ln-fala__leitura">
            <span className="ln-rotulo">caso sintético · cobrança sem solução</span>
            {leitura && leitura.nota !== null ? (
              <>
                <SegmentoLED valor={String(leitura.nota)} rotulo="nota estimada" altura={44} cor="medido" traco="fino" celulas={2} />
                <span className="ln-rotulo">
                  nota estimada · <strong>{leitura.categoria}</strong>
                  <br />o que o Fraus leu nessa conversa
                </span>
              </>
            ) : leitura ? (
              <span className="ln-rotulo">sem sinal · sem nota estimada</span>
            ) : (
              null
            )}
          </figcaption>
        </figure>

        <p className="ln-prosa ln-hero__prosa">
          O Fraus estima satisfação em atendimentos de chatbot, sem pesquisa. Inspecione o contexto antes de agir.
        </p>
        <div className="ln-botoes">
          <a href={leitura ? "#leituras" : "#metodo"} className="ln-botao ln-botao--feixe">
            <IconeDeAcao acao="abrir" />
            {leitura ? "Ver leituras gravadas" : "Entender como funciona"}
          </a>
          <Link href="/entrar" className="ln-botao ln-botao--contorno">
            <IconeDeAcao acao="entrar" />
            Entrar
          </Link>
        </div>
      </div>
    </section>
  );
}
