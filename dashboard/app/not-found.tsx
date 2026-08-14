import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { EstadoVazio } from "@/components/EstadoVazio";

/**
 * 404 proprio.
 *
 * O padrao do Next e uma pagina em ingles, sem a casca do aplicativo e sem
 * saida -- um beco. Aqui ela usa o MESMO estado vazio do resto da interface,
 * pela mesma razao: quando nao ha o que mostrar, a tela diz o que houve e
 * oferece o caminho de volta, em vez de sumir com o produto.
 */
export default function NaoEncontrada() {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-5 px-6 py-10">
      <div className="w-full max-w-lg">
        <p className="num mb-2 text-xs tracking-wide text-muted-foreground">404</p>
        <EstadoVazio
          titulo="Esta página não existe"
          explicacao="O endereço pode ter mudado, ou o atendimento que você procurava foi removido do banco. Nenhum dado foi perdido por causa disto."
        />
        {/*
          `buttonVariants` em vez de `<Button asChild>`: o Button deste chassi
          nao expoe `asChild`, e o elemento certo aqui e uma ancora de verdade
          -- navegacao, nao acao.
        */}
        <div className="mt-4 flex flex-wrap gap-2">
          <Link href="/" className={buttonVariants({ size: "sm" })}>
            Ir para a visão geral
          </Link>
          <Link
            href="/atendimentos"
            className={buttonVariants({ size: "sm", variant: "outline" })}
          >
            Ver atendimentos
          </Link>
        </div>
      </div>
    </main>
  );
}
