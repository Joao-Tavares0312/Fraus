import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { FAMILIAS_DO_VETOR, FATOS_DO_MODELO } from "@/components/lp/fatos";
import { falasDecisivas, marcasDaAtribuicao } from "@/lib/derivacoes";
import type { Leitura } from "@/lib/lp-nova/leituras";

/**
 * A MASCARA QUE VIRA CONSTELACAO -- a secao fixada da vitrine antiga, portada
 * para a cena vgpu. A conversa e a MESMA do hero (a do boleto em dobro), e a
 * nota no fim e a que o motor de producao GRAVOU para ela, com a fala que a
 * puxou; sem gravacao, o estado vazio diz isso. A vitrine antiga tinha aqui um
 * "2,9" digitado a mao sobre uma conversa que nunca passou pelo motor.
 *
 * Quatro passos; o ativo acompanha a cena (`data-fase` na raiz). Sem JS ou
 * com movimento reduzido, os quatro ficam visiveis empilhados.
 */
export function Mascara({ leitura }: { leitura: Leitura | null }) {
  const divisao = FAMILIAS_DO_VETOR.map((f) => `${f.rotulo.toLowerCase()} ${f.qtd}`).join(" · ");
  const decisiva = leitura ? falasDecisivas(marcasDaAtribuicao(leitura.mensagens))[0] : undefined;
  const fala = decisiva ? leitura?.conversa.mensagens[decisiva.indice]?.texto : undefined;

  return (
    <section aria-labelledby="titulo-mascara" className="ln-sec ln-fusor">
      <span data-marco="mascara" className="ln-marco" aria-hidden />
      <span data-marco="nos" className="ln-marco ln-marco--nos" aria-hidden />
      <span data-marco="orbe" className="ln-marco ln-marco--orbe" aria-hidden />
      <div className="ln-wrap ln-fusor__preso">
        <div className="ln-coluna">
          <h2 id="titulo-mascara" className="titulo-vitrine">
            Toda conversa tem uma máscara.
          </h2>
          <ol className="ln-passos">
            <li className="ln-passo" data-passo="mascara">
              <span className="ln-rotulo">o dito · conversa sintética</span>
              <p className="ln-prosa">
                Três tentativas de explicar a cobrança em dobro, três respostas que não ouviram. Para quem lê só a
                última fala, o atendimento terminou bem: <span className="ln-dito">“ok, obrigado 🙂”</span>.
              </p>
            </li>
            <li className="ln-passo" data-passo="mascara">
              <span className="ln-rotulo">a máscara</span>
              <p className="ln-prosa">
                A cortesia é a máscara. Metade dela é <span className="ln-dito">o que o cliente disse</span>; a outra
                metade é <span className="ln-medido">o que dá para medir</span>: o “de novo isso…”, o bot que não
                entendeu, a conversa que acabou sem solução.
              </p>
            </li>
            <li className="ln-passo" data-passo="nos">
              <span className="ln-rotulo">
                {FATOS_DO_MODELO.features} features · {FATOS_DO_MODELO.familias} famílias
              </span>
              <p className="ln-prosa">
                O Fraus desmonta a máscara em {FATOS_DO_MODELO.features} features, um ponto para cada: {divisao}.
              </p>
            </li>
            <li className="ln-passo" data-passo="orbe">
              <span className="ln-rotulo">o fusor</span>
              <p className="ln-prosa">
                Uma regressão logística junta as {FATOS_DO_MODELO.features} numa nota e aponta a fala que a puxou, em
                vez de devolver um número opaco.
              </p>
              {leitura && leitura.nota !== null ? (
                <div className="ln-nota">
                  <SegmentoLED valor={String(leitura.nota)} rotulo="nota estimada desta conversa" altura={48} cor="medido" traco="fino" celulas={2} />
                  <span className="ln-rotulo">
                    nota estimada · <strong>{leitura.categoria}</strong> · lida pelo motor de produção
                  </span>
                  {fala && (
                    <span className="ln-nota__puxou">
                      quem puxou a nota: <q>{fala}</q>
                    </span>
                  )}
                </div>
              ) : (
                <p className="ln-rotulo">a nota desta conversa ainda não foi gravada pelo motor</p>
              )}
            </li>
          </ol>
        </div>
      </div>
    </section>
  );
}
