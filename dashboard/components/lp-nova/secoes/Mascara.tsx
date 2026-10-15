import { IconeDeAcao } from "@/components/IconeDeAcao";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { FAMILIAS_DO_VETOR, FATOS_DO_MODELO } from "@/components/lp/fatos";
import { falasDecisivas, marcasDaAtribuicao } from "@/lib/derivacoes";
import type { Leitura } from "@/lib/lp-nova/leituras";

/**
 * Caso sintetico antes do metodo. A cena acompanha marcos sempre visiveis;
 * abrir o aprofundamento muda o layout, nao inventa resultados ou notas.
 */
export function Mascara({ leitura }: { leitura: Leitura | null }) {
  const divisao = FAMILIAS_DO_VETOR.map((f) => `${f.rotulo.toLowerCase()} ${f.qtd}`).join(" · ");
  const decisiva = leitura ? falasDecisivas(marcasDaAtribuicao(leitura.mensagens))[0] : undefined;
  const fala = decisiva ? leitura?.conversa.mensagens[decisiva.indice]?.texto : undefined;

  return (
    <section id="metodo" data-marco="disperso" aria-labelledby="titulo-mascara" className="ln-sec ln-fusor">
      <div className="ln-wrap ln-fusor__preso">
        <div className="ln-coluna">
          <h2 id="titulo-mascara" data-marco="mascara" className="titulo-vitrine">
            O contexto muda a leitura.
          </h2>
          <div className="ln-caso">
            <p className="ln-rotulo">Conversa sintética · cobrança em dobro</p>
            <p className="ln-prosa">
              O cliente quer corrigir uma cobrança duplicada. O bot oferece uma segunda via,
              sem resolver a reclamação. No fim, o cliente escreve:
            </p>
            <blockquote className="ln-caso__fala">
              <p>“ok, obrigado 🙂”</p>
            </blockquote>
            <p data-marco="nos" className="ln-prosa">
              O encerramento é cortês. A reclamação continua no contexto.
              O Fraus reúne <span className="ln-dito">o que foi dito</span> e{" "}
              <span className="ln-medido">os sinais da conversa</span> para estimar satisfação,
              não para confirmar o que a pessoa sentiu.
            </p>
            <div data-marco="orbe">
              <p className="ln-prosa">
                Uma estimativa é um ponto de partida para inspecionar o atendimento, não um veredito sobre o cliente.
              </p>
              {leitura && leitura.nota !== null ? (
                <div className="ln-nota">
                  <SegmentoLED valor={String(leitura.nota)} rotulo="nota estimada desta conversa" altura={48} cor="medido" traco="fino" celulas={2} />
                  <span className="ln-rotulo">
                    nota estimada · <strong>{leitura.categoria}</strong> · gravada pelo motor real
                  </span>
                  {fala && (
                    <span className="ln-nota__puxou">
                      maior inclinação no classificador de texto: <q>{fala}</q>
                    </span>
                  )}
                </div>
              ) : leitura ? (
                <p className="ln-rotulo">sem sinal · sem nota estimada</p>
              ) : null}
            </div>
          </div>
          <details className="ln-detalhe ln-metodo">
            <summary>
              <span>Como a estimativa é construída</span>
              <IconeDeAcao acao="expandir" />
            </summary>
            <div className="ln-detalhe__corpo">
              <p className="ln-prosa">
                O modelo reúne {FATOS_DO_MODELO.features} features em {FATOS_DO_MODELO.familias} famílias:
                {" "}{divisao}. Os pontos da cena representam essa estrutura, não valores medidos.
              </p>
              <p className="ln-prosa">
                Uma regressão logística combina as features num score; o servidor deriva nota e categoria.
                Os três classificadores BERTimbau leem satisfação, emoção e ironia por mensagem.
                A ironia permanece visível na inspeção, mas não entra no vetor do fusor.
              </p>
              <p className="ln-prosa">
                A probabilidade de cada fala vem do classificador de texto, não mede seu efeito isolado na nota.
                As contribuições do fusor são termos na diferença entre logits de satisfeito e insatisfeito,
                não pontos da nota. O sinal de tempo foi treinado com conversas sintéticas.
              </p>
            </div>
          </details>
        </div>
      </div>
    </section>
  );
}
