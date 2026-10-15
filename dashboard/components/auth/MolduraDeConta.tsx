import Link from "next/link";
import { IconeDeAcao } from "@/components/IconeDeAcao";
import { ArteDeConta } from "./ArteDeConta";
import "./conta.css";

/** A moldura permanece no servidor; a folha cliente anima somente a arte. */
export function MolduraDeConta({
  titulo,
  children,
}: {
  titulo: string;
  children: React.ReactNode;
}) {
  return (
    <main className="conta">
      <aside className="conta-atelier" aria-hidden="true">
        <ArteDeConta />
        <div className="conta-manifesto">
          <p className="conta-assinatura">Fraus</p>
          <p className="conta-frase">A conversa diz.<br />Você vê além.</p>
        </div>
      </aside>
      <section className="conta-acesso" aria-labelledby="conta-titulo">
        <Link className="conta-voltar" href="/">
          <IconeDeAcao acao="anterior" /> Voltar ao site
        </Link>
        <div className="conta-conteudo">
          <Link className="conta-marca" href="/" aria-label="Fraus — início">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/fraus-logo.svg" alt="" width={32} height={32} />
            <span>Fraus</span>
          </Link>
          <h1 id="conta-titulo" className="titulo-vitrine">{titulo}</h1>
          {children}
        </div>
      </section>
    </main>
  );
}
