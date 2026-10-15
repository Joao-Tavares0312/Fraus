import { IconeDeAcao } from "@/components/IconeDeAcao";
import { Problema } from "./Problema";

const LIMITES = [
  {
    frase: "Não pontua atendente.",
    porque:
      "O objeto da análise é o atendimento por chatbot, nunca o desempenho individual de pessoas.",
  },
  {
    frase: "Não roda LLM.",
    porque: "A inferência roda em CPU, sem enviar conversas a APIs de LLM.",
  },
  {
    frase: "Não finge que perguntou.",
    porque: "NPS inferido é uma estimativa, não uma resposta do cliente. O tempo foi treinado com dados sintéticos.",
  },
];

export function Limites() {
  return (
    <section id="limites" aria-labelledby="titulo-limites" className="ln-sec ln-limites">
      <div className="ln-wrap">
        <div className="ln-limites__abertura">
          <h2 id="titulo-limites" className="titulo-vitrine">
            Uma leitura útil sabe onde parar.
          </h2>
          <div className="ln-limites__materia" aria-hidden="true" />
        </div>
        <ul className="ln-limites__lista">
          {LIMITES.map((l) => (
            <li key={l.frase}>
              <h3 className="ln-limites__frase">{l.frase}</h3>
              <p className="ln-prosa">{l.porque}</p>
            </li>
          ))}
        </ul>
        <details className="ln-detalhe">
          <summary>
            <span>Aprofundar limites, pesquisa e uso responsável</span>
            <IconeDeAcao acao="expandir" />
          </summary>
          <div className="ln-detalhe__corpo">
            <p className="ln-prosa">
              O intervalo do NPS mede incerteza amostral, não erro do classificador. Abaixo de 30
              atendimentos com sinal, o ponto não é exibido. Latência e contenção são observadas,
              não estimativas de satisfação. Resultados em conversas sintéticas não demonstram
              desempenho em clientes reais.
            </p>
            <p className="ln-prosa">
              A definição de reconhecimento de emoção do EU AI Act exige dados biométricos.
              Classificar emoção em texto não implica enquadramento automático nessa definição;
              não pontuar atendentes continua sendo uma política firme do Fraus.
            </p>
            <p className="ln-prosa">
              Sem LLM descreve o caminho de predição, não garante por si só conformidade de
              hospedagem, armazenamento ou transporte. Quem opera precisa definir finalidade,
              base legal e acesso aos dados.
            </p>
            <Problema />
          </div>
        </details>
      </div>
    </section>
  );
}
