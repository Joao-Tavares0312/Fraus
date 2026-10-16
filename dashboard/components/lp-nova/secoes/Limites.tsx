import { ChevronDown, CircleOff, ClipboardList, Database, UserRoundX } from "lucide-react";

const LIMITES = [
  { titulo: "Estimativa, não pesquisa", Icone: ClipboardList, texto: "O Fraus estima satisfação a partir dos sinais da conversa. Não lê pensamentos e não substitui uma resposta declarada pelo cliente." },
  { titulo: "Não avalia atendentes", Icone: UserRoundX, texto: "O objeto da análise é o atendimento. O Fraus não produz notas de desempenho para atendentes." },
  { titulo: "Tempo com dados sintéticos", Icone: Database, texto: "O sinal de tempo foi treinado com conversas sintéticas. Essa limitação deve acompanhar a interpretação da estimativa." },
  { titulo: "Sem sinal não é nota zero", Icone: CircleOff, texto: "Sem fala do cliente ou sem sinal para estimar satisfação, a ausência precisa aparecer como ausência. Nunca como uma nota zero." },
];

export function Limites() {
  return (
    <section className="limites" id="limites" aria-labelledby="titulo-limites">
      <div className="limites-conteudo">
        <div className="limites-intro"><h2 id="titulo-limites">Conheça também os limites</h2><p>Uma estimativa ajuda a investigar. Ela não transforma os sinais da conversa em certeza sobre o cliente.</p></div>
        <div className="limites-leituras">
          {LIMITES.map(({ titulo, Icone, texto }, indice) => (
            <details className="limite-detalhe" name="limites-lp" key={titulo} open={indice === 0}>
              <summary><Icone className="icone-lp" aria-hidden="true" /><span>{titulo}</span><ChevronDown className="icone-lp chevron-lp" aria-hidden="true" /></summary>
              <p>{texto}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
