import { MarcaFraus } from "@/components/shell/MarcaFraus";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";

/**
 * A moldura das duas telas de conta (entrar e cadastrar).
 *
 * É a primeira superfície que o usuário toca e por isso ela ecoa o hero da
 * vitrine: título em Bricolage (uma das duas classes autorizadas a usar a
 * display, ver DESIGN.md §4), cartão retangular de hairline, faixa de
 * telemetria em cima e rodapé de honestidade embaixo.
 *
 * O LED de "sessão" está APAGADO de propósito: quem chega aqui ainda não tem
 * sessão, e ausência não é zero — o medidor existe, está ligado e não leu
 * nada. É a invariante 2 do CLAUDE.md desenhada na porta de entrada, e não um
 * enfeite: por isso ele carrega rótulo acessível (`sessão: sem sinal`).
 */
export function MolduraDeConta({
  titulo,
  children,
}: {
  titulo: string;
  children: React.ReactNode;
}) {
  return (
    <main className="flex min-h-svh items-center justify-center p-4">
      <div className="w-full max-w-md border border-linha bg-card">
        <header className="flex items-center justify-between gap-3 border-b border-linha px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <MarcaFraus tamanho={24} />
            <span className="rotulo-instrumento text-foreground">Fraus</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="rotulo-instrumento">sessão</span>
            <SegmentoLED
              valor={null}
              celulas={2}
              altura={14}
              cor="tinta"
              rotulo="sessão"
            />
          </div>
        </header>

        <div className="p-6">
          <p className="rotulo-instrumento mb-3">
            satisfação inferida · estimativa
          </p>
          <h1 className="titulo-vitrine mb-6 text-3xl">{titulo}</h1>
          {children}
        </div>

        <footer className="rotulo-instrumento border-t border-compasso px-4 py-2.5">
          modelos locais · sem LLM em runtime
        </footer>
      </div>
    </main>
  );
}
