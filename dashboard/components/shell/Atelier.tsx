/**
 * O ATELIE: a luz que o vidro refrata.
 *
 * Sem esta camada o reskin de vidro nao existe. Vidro sobre fundo chapado e
 * indistinguivel de um cinza um pouco mais claro, porque nao ha nada atras
 * para refratar -- `backdrop-filter` borra o que esta atras, e atras de um
 * grafite uniforme so ha mais grafite.
 *
 * Tres manchas radiais sobre o `--background`: a da marca, a fria que a
 * contrapesa, e uma terceira fraca que quebra a simetria das duas -- que
 * sozinhas leriam como gradiente de template.
 *
 * As cores vem de `--atelie-marca` / `--atelie-fria` / `--atelie-quente`, e
 * NAO dos tokens de dado. O atelie usava `--dito` e `--medido` emprestados, o
 * que amarrava a iluminacao da sala ao canal que carrega significado. Sao
 * token proprio desde 24/08/2026, o que tambem e o que permite ao tema
 * "chuva de neon" trocar a luz sem encostar no encoding.
 *
 * No tema grafite as tres tem croma BAIXO: elas iluminam, nao pintam. No tema
 * chuva o croma sobe, e pode subir justamente porque esta camada nao carrega
 * dado nenhum -- cor saturada aqui nao inventa canal de significado.
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
        className="absolute -left-[15%] -top-[25%] h-[70vmax] w-[70vmax] rounded-full blur-[80px]"
        style={{
          opacity: "var(--atelie-op-marca)",
          background:
            "radial-gradient(closest-side, var(--atelie-marca), transparent)",
        }}
      />
      {/* fria -- contrapeso do lado do medido, baixo a direita */}
      <div
        className="absolute -bottom-[30%] -right-[20%] h-[75vmax] w-[75vmax] rounded-full blur-[90px]"
        style={{
          opacity: "var(--atelie-op-fria)",
          background:
            "radial-gradient(closest-side, var(--atelie-fria), transparent)",
        }}
      />
      {/* quente fraca -- quebra a simetria das outras duas */}
      <div
        className="absolute left-[45%] top-[55%] h-[45vmax] w-[45vmax] rounded-full blur-[100px]"
        style={{
          opacity: "var(--atelie-op-quente)",
          background:
            "radial-gradient(closest-side, var(--atelie-quente), transparent)",
        }}
      />

      {/* O REFLEXO NO ASFALTO -- so a chuva acende (no grafite a opacidade e
          zero). Faixa larga subindo do rodape: e o que transforma "fundo roxo
          com manchas" em "fachada espelhada no chao molhado". Fica DEPOIS das
          manchas para se somar a elas, e nao por baixo. */}
      <div
        className="absolute inset-x-0 bottom-0 h-[45vh] blur-[60px]"
        style={{
          opacity: "var(--atelie-asfalto)",
          background:
            "linear-gradient(to top, var(--atelie-fria), transparent 78%)",
        }}
      />

      {/* A CHUVA: riscos diagonais finos, ESTATICOS.
          Por que nao cai: a secao 6 do DESIGN.md ja gastou os dois momentos de
          movimento que a interface se permite, e chuva animada seria um
          terceiro que nao comunica estado nenhum -- decoracao pela decoracao,
          rodando atras de tabela e grafico o tempo todo. Estatica ela entrega
          a TEXTURA (o vidro tem o que refratar) sem cobrar quadro nenhum.
          `repeating-linear-gradient` e mascara em vez de mil elementos. */}
      <div
        className="absolute inset-0"
        style={{
          opacity: "var(--atelie-chuva)",
          background:
            "repeating-linear-gradient(74deg, transparent 0 6px, oklch(0.92 0.08 250) 6px 7px, transparent 7px 19px)",
          maskImage:
            "radial-gradient(120% 90% at 50% 0%, black 20%, transparent 75%)",
        }}
      />
    </div>
  );
}
