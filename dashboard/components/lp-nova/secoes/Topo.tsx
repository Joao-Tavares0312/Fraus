import Link from "next/link";
import { MarcaFraus } from "@/components/shell/MarcaFraus";

export function Topo() {
  return (
    <header className="ln-topo">
      <nav aria-label="Navegação principal" className="ln-wrap ln-topo__faixa">
        <Link href="/" aria-label="Fraus — início" className="ln-marca">
          <MarcaFraus tamanho={22} />
          <span>Fraus</span>
        </Link>
        <span className="ln-topo__nota">sem LLM em runtime</span>
        <Link href="/entrar" className="ln-topo__entrar">
          Entrar
        </Link>
      </nav>
    </header>
  );
}
