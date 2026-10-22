import { ChevronDown, ScanText } from "lucide-react";
import type { ConjuntoLeituras, Falta } from "@/lib/lp-nova/leituras";
import { SeletorDeLeituras } from "../SeletorDeLeituras";

export function Leituras({ conjunto }: { conjunto: ConjuntoLeituras | Falta }) {
  if ("falta" in conjunto) {
    return (
      <aside id="leituras" aria-label="Disponibilidade das leituras" className="leituras-ausentes">
        <p role="status"><strong>Leituras gravadas indisponíveis.</strong> {conjunto.falta}. Nenhum resultado é publicado sem uma análise gravada pelo motor real.</p>
      </aside>
    );
  }
  return (
    <details id="leituras" className="leituras-gravadas">
      <summary className="chanfro"><ScanText className="icone-lp" aria-hidden="true" /><span>Inspecionar conversas analisadas</span><ChevronDown className="icone-lp chevron-lp" aria-hidden="true" /></summary>
      <p>Conversas sintéticas escritas para esta página, com análises gravadas pelo motor real. Escolha uma conversa e confira o que foi lido.</p>
      <SeletorDeLeituras conjunto={conjunto} />
    </details>
  );
}
