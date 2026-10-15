import Link from "next/link";
import { IconeDeAcao } from "@/components/IconeDeAcao";
import { MarcaFraus } from "@/components/shell/MarcaFraus";

export function Topo() {
  return (
    <header className="ln-topo">
      <nav aria-label="Navegação principal" className="ln-wrap ln-topo__faixa">
        <Link href="/" aria-label="Fraus — início" className="ln-marca">
          <MarcaFraus tamanho={22} />
          <span>Fraus</span>
        </Link>
        <span className="ln-topo__nota">Sem LLM em runtime</span>
        <div className="ln-topo__acoes">
          <a href="#metodo" className="ln-topo__metodo">Como funciona</a>
          <Link href="/entrar" className="ln-topo__entrar">
            <IconeDeAcao acao="entrar" />
            Entrar
          </Link>
        </div>
      </nav>
    </header>
  );
}
