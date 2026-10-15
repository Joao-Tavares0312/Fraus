/**
 * O PROBLEMA, so com o que tem fonte no repositorio (README, docs/tese.md).
 * Nenhum percentual de mercado inventado.
 */
const FALHAS = [
  {
    nome: "Pesquisa declarada",
    texto:
      "Depende de quem responde e pode deixar parte dos atendimentos sem avaliação. A ausência de resposta não diz como o cliente se sentiu.",
  },
  {
    nome: "Taxa de contenção",
    texto: "Registra se houve transferência, não se o problema foi resolvido. Um atendimento contido também pode terminar em desistência.",
  },
  {
    nome: "Métricas genéricas",
    texto: "Nesse estudo, variáveis genéricas explicaram cerca de 10% da variância da satisfação declarada; com variáveis de domínio, cerca de 27%. Não são medidas de desempenho do Fraus nem um teto universal.",
    fonte: {
      href: "https://link.springer.com/article/10.1007/s41233-025-00071-8",
      rotulo: "Quality and User Experience, Springer, 2025",
    },
  },
];

export function Problema() {
  return (
    <div className="ln-pesquisa">
        <h3 id="titulo-problema">
          O que a pesquisa ajuda a distinguir
        </h3>
        <ul className="ln-linhas">
          {FALHAS.map((f) => (
            <li key={f.nome}>
              <span className="ln-linhas__nome">{f.nome}</span>
              <p className="ln-linhas__texto">
                {f.texto}
                {f.fonte && (
                  <>
                    {" "}
                    <a href={f.fonte.href} className="ln-fonte" target="_blank" rel="noreferrer">
                      {f.fonte.rotulo}
                    </a>
                  </>
                )}
              </p>
            </li>
          ))}
        </ul>
    </div>
  );
}
