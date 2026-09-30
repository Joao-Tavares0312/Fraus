/**
 * O ORBE: o unico elemento vivo da vitrine (Aurora, direcao aprovada em
 * 30/09/2026), reforcado em 30/09/2026 a pedido do dono do projeto.
 *
 * Camadas, de tras para frente: AURA (respira), CORPO (tres manchas em
 * `screen` -- ambar/dito, azul/medido, magenta/atelie --, mais um feixe conico
 * girando por cima), ANEIS orbitais com um satelite cada (as cores dos tres
 * sinais que o orbe mistura), BRILHO especular e o REFLEXO no chao.
 *
 * E cenografia: cor aqui nao e canal de dado. CSS puro, sem canvas e sem
 * requestAnimationFrame; MORA SO NA VITRINE (DESIGN.md, movimento) e
 * `prefers-reduced-motion` recebe tudo PARADO (ver vitrine.css). `aria-hidden`.
 */
export function Orbe() {
  return (
    <div aria-hidden className="vt-orbe">
      <span className="vt-orbe__aura" />
      <div className="vt-orbe__corpo">
        <i />
        <i />
        <i />
        <b className="vt-orbe__feixe" />
        <span className="vt-orbe__brilho" />
      </div>
      <span className="vt-anel vt-anel--1">
        <em />
      </span>
      <span className="vt-anel vt-anel--2">
        <em />
      </span>
      <span className="vt-anel vt-anel--3">
        <em />
      </span>
      <span className="vt-orbe__reflexo" />
    </div>
  );
}
