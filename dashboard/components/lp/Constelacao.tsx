import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { FAMILIAS_DO_VETOR, FATOS_DO_MODELO } from "./fatos";

/**
 * A MASCARA QUE VIRA CONSTELACAO -- a secao fixada da vitrine.
 *
 * As palavras da conversa (sintetica, e dito assim) viram pontos, os pontos
 * montam uma mascara (metade ambar, o dito; metade azul, o medido), a mascara
 * se desfaz em um no por feature agrupado na contagem real de cada familia, e
 * os nos caem no orbe, que e o fusor. Quem desenha e o motor, no canvas; aqui
 * fica o texto, que e o que o leitor de tela e o regime parado leem.
 *
 * Sem JavaScript (ou com `prefers-reduced-motion`) os quatro passos aparecem
 * empilhados e a nota fica visivel: conteudo legivel em repouso.
 */
export function Constelacao() {
  const divisao = FAMILIAS_DO_VETOR.map((f) => `${f.rotulo.toLowerCase()} ${f.qtd}`).join(" · ");

  return (
    <section id="constelacao" aria-labelledby="titulo-constelacao" className="vt-const">
      <div className="vt-const__pin" data-vt="pin">
        <div className="vt-wrap vt-const__grade">
          <div className="vt-const__texto">
            <h2 id="titulo-constelacao" className="titulo-vitrine">
              Toda conversa tem uma máscara.
            </h2>
            <ol className="vt-passos">
              <li className="vt-passo" data-vt="passo" data-ativo="">
                <span className="vt-rotulo">o dito · amostra sintética</span>
                <p className="vt-prosa">
                  Três falas em cinco minutos. Para quem lê só a última, o
                  atendimento terminou bem:{" "}
                  <span className="vt-dito">“tá. ok, obrigado 🙂”</span>.
                </p>
              </li>
              <li className="vt-passo" data-vt="passo">
                <span className="vt-rotulo">a máscara</span>
                <p className="vt-prosa">
                  A cortesia é a máscara. Metade dela é{" "}
                  <span className="vt-dito">o que o cliente disse</span>; a outra
                  metade é <span className="vt-medido">o que dá para medir</span>:
                  a pausa de 4:12, o emoji no fim, o “quebrado” duas falas antes.
                </p>
              </li>
              <li className="vt-passo" data-vt="passo">
                <span className="vt-rotulo">
                  {FATOS_DO_MODELO.features} features · {FATOS_DO_MODELO.familias} famílias
                </span>
                <p className="vt-prosa">
                  O Fraus desmonta a máscara em {FATOS_DO_MODELO.features}{" "}
                  features: {divisao}.
                </p>
              </li>
              <li className="vt-passo" data-vt="passo">
                <span className="vt-rotulo">o fusor</span>
                <p className="vt-prosa">
                  Uma regressão logística junta as {FATOS_DO_MODELO.features} numa
                  nota — e aponta a fala que a puxou, em vez de devolver um
                  número opaco.
                </p>
              </li>
            </ol>
            <div className="vt-nota" data-vt="nota-fim">
              <SegmentoLED
                valor="2,9"
                rotulo="nota estimada, amostra sintética"
                altura={52}
                traco="fino"
                className="vt-nota__led"
              />
              <span className="vt-rotulo">nota estimada · 0–10</span>
              <span className="vt-rotulo vt-nota__classe">detrator · amostra sintética</span>
              <span className="vt-nota__puxou">↑ quem puxou a nota: a fala de 14:02:10</span>
            </div>
          </div>
          <div aria-hidden className="vt-palco" data-vt="palco" />
        </div>
        <div className="sr-only">
          <p>
            Conversa sintética. Cliente, 14:02:10: “Meu pedido chegou quebrado pela
            terceira vez.” Atendente virtual, 14:02:48: “Sinto muito. Vou abrir uma
            solicitação.” Cliente, 14:07:00, depois de 4 minutos e 12 segundos:
            “tá. ok, obrigado”, com emoji sorridente.
          </p>
        </div>
      </div>
    </section>
  );
}
