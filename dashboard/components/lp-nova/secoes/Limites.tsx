const LIMITES = [
  {
    frase: "Não pontua atendente.",
    porque:
      "Reconhecer emoção no local de trabalho é proibido pelo EU AI Act desde fevereiro de 2025. O Fraus lê o atendimento, nunca a pessoa que atendeu.",
  },
  {
    frase: "Não roda LLM.",
    porque: "Toda leitura é inferência local em CPU, com modelos treinados para isso. Nenhuma conversa sai para um serviço de terceiros.",
  },
  {
    frase: "Não finge que perguntou.",
    porque: "O NPS é estimado do texto e aparece como estimativa em toda tela. O sinal de tempo vem de dados sintéticos, e isso está escrito.",
  },
];

export function Limites() {
  return (
    <section aria-labelledby="titulo-limites" className="ln-sec ln-limites">
      <div className="ln-wrap">
        <h2 id="titulo-limites" className="ln-sr">
          O que o Fraus não faz
        </h2>
        <ul className="ln-limites__lista">
          {LIMITES.map((l) => (
            <li key={l.frase}>
              <p className="titulo-vitrine ln-limites__frase">{l.frase}</p>
              <p className="ln-prosa">{l.porque}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
