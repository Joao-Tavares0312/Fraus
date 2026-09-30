import Link from "next/link";
import { ArrowDown, ArrowRight } from "lucide-react";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { formatarSegundosLED } from "@/lib/formato";
import { Orbe } from "./Orbe";

/**
 * A AMOSTRA SINTETICA da vitrine -- uma conversa inventada, rotulada como tal
 * em TODO lugar onde aparece. E a mesma frase do PRODUCT.md ("ok, obrigado
 * 🙂" e sai insatisfeito), 252 s de pausa e uma nota de exemplo. Nada aqui e
 * medicao real; o Fraus so tem dado sintetico hoje e isso e dito, nao
 * escondido.
 */
const LATENCIA_AMOSTRA = formatarSegundosLED(252); // 4 min 12 s

/** Os fatos verdadeiros do produto (CLAUDE.md), em LED dourado. */
const FATOS = [
  ["famílias de sinal", "07"],
  ["features no fusor", "39"],
  ["BERTimbau fine-tunados", "03"],
  ["LLMs na inferência", "00"],
] as const;

export function Hero() {
  return (
    <section
      aria-labelledby="titulo-hero"
      className="vt-hero"
    >
      <div aria-hidden className="vt-halo" />
      <div aria-hidden className="vt-grao" />

      <div className="vt-wrap flex flex-1 flex-col">
        <div className="vt-palco">
          <div className="vt-orbe-cel">
            <Orbe />
          </div>

          <div className="vt-titulo">
            <h1 id="titulo-hero" className="display-vitrine">
              <span>Leia o que ficou</span> <span>nas entrelinhas.</span>
            </h1>
          </div>

          <p className="vt-sub">
            A mesma conversa, lida por sete sinais: o que foi dito acima da
            linha, o que foi medido abaixo.
          </p>

          <div className="vt-cta">
            <Link href="/entrar" className="vt-botao vt-botao--feixe">
              Iniciar leitura <ArrowRight aria-hidden />
            </Link>
            <a href="#leitura" className="vt-botao vt-botao--contorno">
              Ver uma análise <ArrowDown aria-hidden />
            </a>
          </div>

          <div className="vt-cel-esq">
            <figure className="vt-fala">
              <figcaption className="vt-fala__quem">
                dito · atendimento a-0041
              </figcaption>
              <blockquote>
                <mark>tá. ok, obrigado</mark> 🙂
              </blockquote>
            </figure>
          </div>

          <div className="vt-cel-dir">
            <div className="vt-leitura" role="group" aria-label="Leitura de uma amostra sintética">
              <div>
                <span className="vt-leitura__rotulo">nota estimada · 0–10</span>
                <SegmentoLED
                  className="vt-leitura__valor"
                  valor="2,9"
                  altura={58}
                  rotulo="nota estimada, amostra sintética"
                />
                <p className="vt-leitura__nota">● detrator · amostra sintética</p>
              </div>
              <div>
                <span className="vt-leitura__rotulo">latência da resposta</span>
                <SegmentoLED
                  className="vt-leitura__valor"
                  valor={LATENCIA_AMOSTRA.valor}
                  altura={30}
                  rotulo="latência da resposta, minutos e segundos"
                />
                <p className="vt-leitura__nota">
                  {LATENCIA_AMOSTRA.unidade} · pausa longa
                </p>
              </div>
              <div>
                <span className="vt-leitura__rotulo">
                  atendimento sem fala do cliente
                </span>
                <SegmentoLED
                  className="vt-leitura__valor"
                  valor={null}
                  altura={22}
                  cor="tinta"
                  rotulo="nota do atendimento sem fala do cliente"
                />
                <p className="vt-leitura__nota">○ sem sinal · não é zero</p>
              </div>
            </div>
          </div>
        </div>

        <div className="vt-fatos">
          <div className="vt-fatos__grade" role="list" aria-label="Fatos do modelo">
            {FATOS.map(([rotulo, valor]) => (
              <div key={rotulo} role="listitem">
                <span>{rotulo}</span>
                <SegmentoLED
                  valor={valor}
                  altura={46}
                  cor="marca"
                  rotulo={rotulo}
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
