/**
 * O ATELIE: a luz que o vidro refrata.
 *
 * Sem esta camada o reskin de vidro nao existe. Vidro sobre fundo chapado e
 * indistinguivel de um cinza um pouco mais claro, porque nao ha nada atras
 * para refratar -- `backdrop-filter` borra o que esta atras, e atras de um
 * grafite uniforme so ha mais grafite.
 *
 * Tres manchas radiais de croma BAIXO sobre o `--background`: elas iluminam,
 * nao pintam. A dourada e a marca; a fria contrapesa do lado do `--medido`; a
 * quente fraca quebra a simetria das duas, que sozinhas leriam como gradiente
 * de template.
 *
 * E ESTATICO, e isso e uma decisao, nao uma pendencia. A alternativa avaliada
 * -- a luz mudar de cor conforme o resultado do periodo -- foi rejeitada: ela
 * criaria um canal de cor sem rotulo, contra o principio de que categoria
 * nunca e comunicada so por cor, e contra a regra de que a cor da marca nunca
 * codifica valor. Ver DESIGN.md, seccao 3.3.
 *
 * `aria-hidden` e `pointer-events-none` porque isto nao e conteudo nem alvo:
 * e o papel de parede da sala.
 */
export function Atelier() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-background"
    >
      {/* dourada -- a marca, alto a esquerda */}
      <div
        className="absolute -left-[15%] -top-[25%] h-[70vmax] w-[70vmax] rounded-full opacity-[0.13] blur-[80px]"
        style={{
          background:
            "radial-gradient(closest-side, var(--primary), transparent)",
        }}
      />
      {/* fria -- contrapeso do lado do medido, baixo a direita */}
      <div
        className="absolute -bottom-[30%] -right-[20%] h-[75vmax] w-[75vmax] rounded-full opacity-[0.11] blur-[90px]"
        style={{
          background:
            "radial-gradient(closest-side, var(--medido), transparent)",
        }}
      />
      {/* quente fraca -- quebra a simetria das outras duas */}
      <div
        className="absolute left-[45%] top-[55%] h-[45vmax] w-[45vmax] rounded-full opacity-[0.07] blur-[100px]"
        style={{
          background: "radial-gradient(closest-side, var(--dito), transparent)",
        }}
      />
    </div>
  );
}
