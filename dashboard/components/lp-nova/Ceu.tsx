import type { CSSProperties } from "react";
import { gerarCeu, SEMENTE_CEU } from "@/lib/lp-nova/ceu";

const ceu = gerarCeu(SEMENTE_CEU);

/** Fundo vivo da LP: renderizado no servidor, so opacity/transform animam. */
export function Ceu() {
  return (
    <div className="lp-ceu" aria-hidden="true">
      {ceu.pontos.map((p, i) => (
        <i
          key={`p${i}`}
          className={p.pisca ? "lp-ponto pisca" : "lp-ponto"}
          style={{
            left: `${p.x}%`,
            top: `${p.y}%`,
            "--s": `${p.tamanho}px`,
            "--o": p.opacidade,
            "--d": `${p.ciclo}s`,
            animationDelay: `${p.atraso}s`,
          } as CSSProperties}
        />
      ))}
      {ceu.riscos.map((r, i) => (
        <b
          key={`r${i}`}
          className="lp-risco"
          style={{
            left: `${r.x}%`,
            top: `${r.y}%`,
            "--l": `${r.comprimento}px`,
            "--a": r.alfa,
            animationDuration: `${r.duracao}s`,
            animationDelay: `${r.atraso}s`,
          } as CSSProperties}
        />
      ))}
    </div>
  );
}
