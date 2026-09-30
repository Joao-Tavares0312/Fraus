import { EtiquetaCategoria } from "@/components/EtiquetaCategoria";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { formatarSegundosLED } from "@/lib/formato";
import { Revelar } from "./Revelar";

const PAUSA = formatarSegundosLED(252); // 4 min 12 s, amostra sintetica

/**
 * A LEITURA: a regua que governa o Fraus (DESIGN.md secao 1), desenhada como
 * hero de secao. Acima da linha, o que foi DITO -- em cartoes retangulares com
 * o filete ambar; abaixo, o que foi MEDIDO -- a pausa notada em escala e os
 * sinais lidos.
 *
 * Nao ha balao, tom de pontos nem efeito sonoro: a direcao "Tinta e tom" foi
 * retirada da fusao por decisao do dono do projeto. O que faz o trabalho aqui
 * e a propria notacao -- linha, barra de compasso, pausa e ligadura --, que o
 * DESIGN.md ja definia sem desenhar glifo musical.
 *
 * TUDO nesta secao e amostra SINTETICA e o cabecalho da regua diz isso.
 */
export function Leitura() {
  return (
    <section id="leitura" aria-labelledby="titulo-leitura" className="vt-sec">
      <div className="vt-wrap vt-leitura-sec">
        <Revelar>
          <h2 id="titulo-leitura" className="titulo-vitrine max-w-[12ch]">
            A cortesia mascara. O contexto denuncia.
          </h2>
          <p className="vt-prosa mt-8">
            No fim da conversa, o cliente escreve “ok, obrigado 🙂”. Sozinho, o
            texto soa promotor. A pausa, a emoção e o emoji contra o texto
            contam outra história — e o Fraus aponta qual trecho puxou a nota,
            em vez de devolver um número opaco.
          </p>
        </Revelar>

        <Revelar>
          <figure
            className="vt-regua"
            aria-label="Régua de uma conversa de amostra: acima, o que foi dito; abaixo, o que foi medido"
          >
            <figcaption className="vt-regua__cab">
              <span>régua · cliente × atendente virtual</span>
              <span>amostra sintética</span>
            </figcaption>

            <div className="vt-regua__zona vt-regua__acima">
              <span className="vt-regua__lado is-dito">acima · dito</span>

              <div className="vt-fala-g1">
                <blockquote className="vt-fala">
                  <span className="vt-fala__quem">cliente · 14:02</span>
                  Meu pedido chegou quebrado <mark>pela terceira vez</mark>.
                </blockquote>
                <p className="vt-ligadura">puxou a nota ↓</p>
              </div>

              <div className="vt-fala vt-fala--bot vt-fala-bot">
                <span className="vt-fala__quem">atendente virtual · 14:02</span>
                Sinto muito. Vou abrir uma solicitação.
              </div>

              <div className="vt-fala-g2">
                <blockquote className="vt-fala">
                  <span className="vt-fala__quem">cliente · 14:07</span>
                  <mark>tá. ok, obrigado</mark> 🙂
                </blockquote>
              </div>
            </div>

            <div aria-hidden className="vt-regua__linha" />

            <div className="vt-regua__zona vt-regua__abaixo">
              <span className="vt-regua__lado is-medido">abaixo · medido</span>

              <div className="vt-pausa">
                <span className="vt-pausa__rotulo">
                  pausa
                  <SegmentoLED
                    valor={PAUSA.valor}
                    altura={26}
                    rotulo="pausa entre as falas, minutos e segundos"
                  />
                  {PAUSA.unidade} · proporcional
                </span>
              </div>

              <ul className="vt-chips" aria-label="Sinais medidos nesta conversa">
                <li>emoção · raiva → neutro</li>
                <li>emoji × texto · incongruente</li>
                <li>evidência · 2 falas do cliente</li>
              </ul>

              <div className="vt-nota">
                <span className="vt-leitura__rotulo">nota estimada</span>
                <SegmentoLED
                  valor="2,9"
                  altura={84}
                  rotulo="nota estimada, amostra sintética"
                />
                <EtiquetaCategoria categoria="detrator" />
              </div>
            </div>
          </figure>
        </Revelar>
      </div>
    </section>
  );
}
