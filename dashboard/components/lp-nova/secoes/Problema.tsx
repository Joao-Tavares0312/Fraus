/**
 * O PROBLEMA, so com o que tem fonte no repositorio (README, docs/tese.md).
 * Nenhum percentual de mercado inventado.
 */
const FALHAS = [
  {
    nome: "Pesquisa declarada",
    texto:
      "Depende de resposta, e responde quem ficou muito irritado ou muito satisfeito. O cliente do meio, que resolveu com esforço ou desistiu, não aparece.",
  },
  {
    nome: "Taxa de contenção",
    texto: "Mede volume, não qualidade: sobe igual quando o bot resolve e quando o cliente desiste de tentar.",
  },
  {
    nome: "Métricas genéricas",
    texto: "Número de mensagens e intents previstos explicam cerca de 10% da variância da satisfação declarada.",
    fonte: {
      href: "https://link.springer.com/article/10.1007/s41233-025-00071-8",
      rotulo: "Quality and User Experience, Springer, 2025",
    },
  },
];

export function Problema() {
  return (
    <section data-marco="disperso" aria-labelledby="titulo-problema" className="ln-sec ln-problema">
      <div className="ln-wrap">
        <div className="ln-coluna">
        <h2 id="titulo-problema" className="titulo-vitrine">
          A nota declarada mente. E quase ninguém declara.
        </h2>
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
      </div>
    </section>
  );
}
