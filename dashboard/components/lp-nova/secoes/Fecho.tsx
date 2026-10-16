import Link from "next/link";
import { LogIn, UserRoundPlus } from "lucide-react";

export function Fecho() {
  return (
    <footer className="fecho">
      <div className="fecho-marca"><span>Fraus</span><p>Contexto, não certeza.</p></div>
      <div className="fecho-acoes">
        <Link href="/entrar" prefetch={false} className="acao-lp"><LogIn className="icone-lp" aria-hidden="true" />Entrar no Fraus</Link>
        <Link href="/cadastrar" prefetch={false} className="acao-lp secundaria"><UserRoundPlus className="icone-lp" aria-hidden="true" />Criar conta</Link>
      </div>
    </footer>
  );
}
