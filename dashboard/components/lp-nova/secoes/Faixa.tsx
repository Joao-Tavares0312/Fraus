const PAINEIS = [
  { voz: "d", rotulo: "Dito · 01", nome: "TEXTO", texto: "O que o cliente escreveu, lido fala a fala." },
  { voz: "d", rotulo: "Dito · 02", nome: "EMOJIS", texto: "O que o texto sozinho não diz." },
  { voz: "m", rotulo: "Medido · 03", nome: "TEMPO", texto: "Latências derivadas dos timestamps das mensagens." },
] as const;

/** Letreiro: decorativo, a mesma ideia ja esta no texto da pagina. */
export function Letreiro() {
  const itens = ["Contexto", "não certeza", "Dito", "Medido"];
  return (
    <div className="mq" aria-hidden="true">
      <div data-letreiro>{[...itens, ...itens].map((item, i) => <span key={i}>{item}</span>)}</div>
    </div>
  );
}

/** Vitrine horizontal fixada pela rolagem; com reduce vira lista vertical. */
export function Faixa() {
  return (
    <section id="faixa" aria-label="O que o Fraus lê">
      <div className="trk">
        {PAINEIS.map(({ voz, rotulo, nome, texto }) => (
          <div className="pn" key={nome}>
            <span className={`tag ${voz}`} data-embaralhar>{rotulo}</span>
            <h3 className="big">{nome}</h3>
            <p>{texto}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
