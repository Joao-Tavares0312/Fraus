/**
 * O ORBE: o unico elemento vivo da vitrine (Aurora, direcao aprovada em
 * 30/09/2026).
 *
 * Tres manchas radiais em `mix-blend-mode: screen`, cada uma girando num
 * periodo primo com o das outras (14 / 18 / 22 s), entao a composicao nunca
 * fecha o ciclo dentro de uma visita. As cores sao AMBAR (`--dito`), AZUL
 * (`--medido`) e o magenta do atelie (`--atelie-halo`): cenografia, e por isso
 * pode ter croma alto sem inventar canal de significado -- o dado, na pagina,
 * continua sendo so o que esta escrito e tem rotulo.
 *
 * MORA SO AQUI. A ferramenta e lida por horas e nao pode ter GPU girando atras
 * de tabela e grafico; a vitrine e visita curta (DESIGN.md secoes 6 e 8.7). E
 * CSS puro, sem canvas e sem requestAnimationFrame: o compositor cuida da
 * rotacao. `prefers-reduced-motion` recebe o orbe PARADO (ver vitrine.css).
 *
 * `aria-hidden`: nao e conteudo nem alvo.
 */
export function Orbe() {
  return (
    <div aria-hidden className="vt-orbe">
      <i />
      <i />
      <i />
    </div>
  );
}
