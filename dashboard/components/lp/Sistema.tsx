import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { FAMILIAS_DO_VETOR, FATOS_DO_MODELO, emDuasCasas } from "./fatos";

const FATOS = [
  ["famílias no vetor", FATOS_DO_MODELO.familias],
  ["features no fusor", FATOS_DO_MODELO.features],
  ["BERTimbau fine-tunados", FATOS_DO_MODELO.bertimbau],
  ["LLMs na inferência", FATOS_DO_MODELO.llms],
] as const;

/**
 * O SISTEMA, em linhas e nao em cartoes (pedido do Joao: cartao detalhado
 * puxa atencao demais). Cada familia com o que le e quantas features entrega
 * -- a contagem vem de `FAMILIAS_DO_VETOR`, guardada contra `NOMES_FEATURES`.
 */
export function Sistema() {
  return (
    <section id="sistema" aria-labelledby="titulo-sistema" className="vt-sec">
      <div className="vt-wrap">
        <div className="vt-sistema__cab">
          <h2 id="titulo-sistema" className="titulo-vitrine">
            Sete famílias no vetor. Nenhuma chamada de rede.
          </h2>
          <p className="vt-prosa">
            Cada família lê um aspecto da conversa e entrega features a um fusor
            treinado. Tudo roda local, em CPU: o atendimento não sai da máquina
            para ser pontuado.
          </p>
        </div>
        <ul className="vt-linhas">
          {FAMILIAS_DO_VETOR.map((f) => (
            <li key={f.chave}>
              <span className="vt-linhas__nome">{f.rotulo}</span>
              <span className="vt-linhas__desc">{f.leitura}</span>
              <span className="vt-linhas__qtd">{f.qtd} features</span>
            </li>
          ))}
          <li className="vt-linhas__fusor">
            <span className="vt-linhas__nome">Fusor</span>
            <span className="vt-linhas__desc">
              Regressão logística sobre as {FATOS_DO_MODELO.features}. Score 0–100,
              nota 0–10 e categoria de NPS derivados no servidor.
            </span>
            <span className="vt-linhas__qtd">{FATOS_DO_MODELO.features} → 1</span>
          </li>
        </ul>
        <div className="vt-fatos" role="list" aria-label="Fatos do modelo">
          {FATOS.map(([rotulo, valor]) => (
            <div key={rotulo} role="listitem">
              <span className="vt-rotulo">{rotulo}</span>
              <SegmentoLED valor={emDuasCasas(valor)} rotulo={rotulo} altura={34} cor="tinta" traco="fino" />
            </div>
          ))}
        </div>
        <p className="vt-ressalva">
          A cabeça de ironia continua lida por mensagem, mas saiu do vetor em
          04/09/2026: no corpus de treino ela media sentimento positivo, não
          ironia. O Fraus reconhece emoção no texto do cliente — e não pontua
          atendentes.
        </p>
      </div>
    </section>
  );
}
