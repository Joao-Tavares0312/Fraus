import Link from "next/link";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import type { Leitura } from "@/lib/lp-nova/leituras";

/**
 * O HERO: a mentira educada, em tres linhas. A fala do cliente esta no DOM
 * (legivel sem JavaScript, e o que o leitor de tela le); com a cena viva ela
 * fica transparente e as particulas ambar ocupam exatamente os mesmos pixels.
 */
export function Hero({ leitura }: { leitura: Leitura | null }) {
  return (
    <section id="topo" data-marco="frase" aria-labelledby="titulo-ln" className="ln-hero">
      <div className="ln-wrap ln-hero__miolo">
        <h1 id="titulo-ln" className="display-vitrine ln-hero__titulo">
          O cliente disse obrigado. <span className="ln-medido">Saiu insatisfeito.</span>
        </h1>

        <figure className="ln-fala">
          <blockquote>
            <p data-ln="frase" className="ln-fala__texto">
              ok, obrigado 🙂
            </p>
          </blockquote>
          <figcaption className="ln-fala__leitura">
            {leitura && leitura.nota !== null ? (
              <>
                <SegmentoLED valor={String(leitura.nota)} rotulo="nota estimada" altura={44} cor="medido" traco="fino" celulas={2} />
                <span className="ln-rotulo">
                  nota estimada · <strong>{leitura.categoria}</strong>
                  <br />o que o Fraus leu nessa conversa
                </span>
              </>
            ) : (
              <span className="ln-rotulo">leitura desta conversa ainda não gravada</span>
            )}
          </figcaption>
        </figure>

        <p className="ln-prosa ln-hero__prosa">
          O Fraus mede a satisfação em atendimentos de chatbot sem perguntar nada ao cliente. Sete famílias de sinal
          leem a mesma conversa, e cada nota aponta a fala que a puxou.
        </p>
        <div className="ln-botoes">
          <a href="#leituras" className="ln-botao ln-botao--feixe">
            Ver o Fraus ler ↓
          </a>
          <Link href="/entrar" className="ln-botao ln-botao--contorno">
            Entrar
          </Link>
        </div>
      </div>
    </section>
  );
}
