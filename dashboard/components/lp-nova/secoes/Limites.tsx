import { Palavras } from "../Palavras";

const LIMITES = [
  { titulo: "Estimativa, não pesquisa", texto: "Não lê pensamentos e não substitui uma resposta declarada pelo cliente." },
  { titulo: "Não avalia atendentes", texto: "O objeto da análise é o atendimento, não quem atendeu." },
  { titulo: "Tempo com dados sintéticos", texto: "O sinal de tempo foi treinado com conversas sintéticas." },
  { titulo: "Sem sinal não é nota zero", texto: "A ausência aparece como ausência. Nunca como nota zero." },
];

export function Limites() {
  return (
    <section id="limites" className="cena c" aria-labelledby="titulo-limites">
      <div className="blk">
        <p className="ouro sobretitulo">Contexto, não certeza.</p>
        <h2 id="titulo-limites"><Palavras texto="Conheça também os limites" /></h2>
        <div className="grid">
          {LIMITES.map(({ titulo, texto }) => <div className="card placas fio rv" key={titulo}><h3>{titulo}</h3><p>{texto}</p></div>)}
        </div>
      </div>
    </section>
  );
}
