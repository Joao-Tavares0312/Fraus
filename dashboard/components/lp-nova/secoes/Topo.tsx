import Link from "next/link";
import Image from "next/image";
import { LogIn } from "lucide-react";

export function Topo() {
  return (
    <header className="lp-cabecalho">
      <Link className="marca" href="/" aria-label="Fraus, início"><Image src="/fraus-logo.svg" alt="" width={42} height={42} /><span>Fraus</span></Link>
      <nav aria-label="Navegação principal">
        <a href="#como-funciona">Como funciona</a>
        <a href="#na-pratica">Na prática</a>
        <a href="#limites">Limites</a>
        <Link className="entrar-lp" href="/entrar" prefetch={false}><LogIn className="icone-lp" aria-hidden="true" />Entrar</Link>
      </nav>
    </header>
  );
}
