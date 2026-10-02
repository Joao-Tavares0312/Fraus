import Link from "next/link";

/**
 * O HERO, aprovado na rodada de prototipos (v0, 01/10/2026): a manchete
 * gigante a esquerda e o orbe a direita -- o orbe nao e elemento daqui, e o
 * canvas da cena, que atravessa a pagina inteira. O "entrelinhas" vai em
 * ambar porque e o dito: o que o cliente escreveu.
 */
export function Hero() {
  return (
    <section id="hero" aria-labelledby="titulo-hero" className="vt-hero">
      <div className="vt-wrap vt-hero__miolo">
        <h1 id="titulo-hero" className="display-vitrine" data-vt="titulo-hero">
          <span className="vt-linha"><span>Leia o que</span></span>
          <span className="vt-linha"><span>ficou nas</span></span>
          <span className="vt-linha"><span className="vt-dito">entrelinhas.</span></span>
        </h1>
        <div className="vt-hero__base">
          <div>
            <p className="vt-prosa">
              O Fraus mede a satisfação em atendimentos de chatbot sem perguntar
              nada ao cliente. Sete famílias de sinal leem a mesma conversa — e
              nenhum LLM roda na inferência.
            </p>
            <div className="vt-botoes">
              <Link href="/entrar" className="vt-botao vt-botao--feixe">
                Iniciar leitura →
              </Link>
              <a href="#constelacao" className="vt-botao vt-botao--contorno">
                Ver uma análise ↓
              </a>
            </div>
          </div>
          <div className="vt-deixa">
            <span className="vt-rotulo">role · a leitura começa pela fala do cliente</span>
            <span aria-hidden className="vt-deixa__seta" />
          </div>
        </div>
      </div>
    </section>
  );
}
