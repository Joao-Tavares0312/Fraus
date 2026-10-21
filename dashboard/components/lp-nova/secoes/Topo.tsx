import Image from "next/image";
import Link from "next/link";

export function Topo() {
  return (
    <header className="lp-cabecalho">
      <Link className="marca" href="/" aria-label="Fraus, início"><Image src="/fraus-logo.svg" alt="" width={30} height={30} /><span>Fraus</span></Link>
      <nav aria-label="Navegação principal">
        <a href="#como-funciona" data-embaralhar>Como funciona</a>
        <a href="#na-pratica" data-embaralhar>Na prática</a>
        <a href="#limites" data-embaralhar>Limites</a>
        <Link className="btn o chanfro fio-hover mag entrar-lp" href="/entrar" prefetch={false} data-embaralhar>Entrar</Link>
      </nav>
    </header>
  );
}
