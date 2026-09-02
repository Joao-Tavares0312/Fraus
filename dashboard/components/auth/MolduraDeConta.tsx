import { MarcaFraus } from "@/components/shell/MarcaFraus";

/**
 * A moldura das duas telas de conta (entrar e cadastrar). Vidro médio, como
 * as superfícies de trabalho — a tela de entrar é a primeira superfície que o
 * usuário toca, e ela já é o produto.
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
      <div className="vidro w-full max-w-sm p-6">
        <div className="mb-6 flex items-center gap-3">
          <MarcaFraus tamanho={32} />
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-tight">Fraus</span>
            <span className="text-xs text-muted-foreground">
              satisfação inferida
            </span>
          </div>
        </div>
        <h1 className="mb-4 text-lg font-semibold tracking-tight">{titulo}</h1>
        {children}
      </div>
    </main>
  );
}
