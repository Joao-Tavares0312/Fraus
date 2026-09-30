import { ShieldCheck } from "lucide-react";
import { Revelar } from "./Revelar";

/**
 * Os textos de HONESTIDADE do produto (PRODUCT.md, "Brand Commitments"):
 * permanecem, e na vitrine ganham o lugar de secao inteira, nao de rodape.
 */
const AVISOS = [
  [
    "01",
    "É estimativa, não pesquisa",
    "O NPS é inferido da conversa e nunca aparece como nota declarada pelo cliente.",
  ],
  [
    "02",
    "Ausência não vira zero",
    "Sem fala suficiente, o atendimento aparece como sem sinal. Não medir e medir insatisfação são respostas diferentes.",
  ],
  [
    "03",
    "Limitação não é rodapé",
    "O sinal de tempo usa dados sintéticos por falta de corpus público com timestamps de diálogo. Isso permanece visível.",
  ],
] as const;

/**
 * O QUE O FRAUS LE E O QUE ELE NAO FAZ -- resumo de docs/conformidade.md.
 *
 * O documento e cuidadoso e a vitrine tambem precisa ser: o Fraus infere
 * emocao a partir de TEXTO de chat (nao de dado biometrico), entao esta secao
 * NAO afirma enquadramento legal nenhum. Ela diz o que o produto faz, a quem
 * ele se aplica e a fronteira que ele mesmo se impoe: nao pontua atendentes.
 */
export function Metodo() {
  return (
    <section id="metodo" aria-labelledby="titulo-metodo" className="vt-sec">
      <div className="vt-wrap vt-metodo">
        <Revelar>
          <h2 id="titulo-metodo" className="titulo-vitrine max-w-[12ch]">
            Um modelo que mostra os próprios limites.
          </h2>
          <p className="mt-8 flex gap-3 text-sm text-muted-foreground">
            <ShieldCheck aria-hidden className="mt-0.5 size-4 shrink-0" />
            Sem número inventado. Sem depoimento fabricado.
          </p>
        </Revelar>

        <Revelar>
          <div className="border-t border-linha">
            {AVISOS.map(([no, titulo, texto]) => (
              <article key={no} className="vt-aviso">
                <span className="vt-aviso__no num">{no}</span>
                <div>
                  <h3>{titulo}</h3>
                  <p>{texto}</p>
                </div>
              </article>
            ))}
          </div>

          <aside className="vt-limite" aria-label="O que o Fraus lê e o que ele não faz">
            <h3>o que o fraus lê · o que ele não faz</h3>
            <ul>
              <li>
                Lê a <b>emoção do cliente</b> no texto e diz isso, junto da nota,
                em toda tela onde a leitura aparece.
              </li>
              <li>
                <b>Não pontua atendentes.</b> É regra do produto: o atendente
                aparece na conversa como contexto, nunca como alvo de nota.
              </li>
              <li>
                Roda em lote, sobre conversa já encerrada, e <b>não decide nada
                sozinho</b>.
              </li>
            </ul>
          </aside>
        </Revelar>
      </div>
    </section>
  );
}
