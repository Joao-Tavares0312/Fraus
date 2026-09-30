import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { EstadoVazio } from "@/components/EstadoVazio";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";

/**
 * 404 proprio.
 *
 * O padrao do Next e uma pagina em ingles, sem a casca do aplicativo e sem
 * saida -- um beco. Aqui ela usa o MESMO estado vazio do resto da interface,
 * pela mesma razao: quando nao ha o que mostrar, a tela diz o que houve e
 * oferece o caminho de volta, em vez de sumir com o produto.
 *
 * O "404" e o proprio codigo HTTP lido no display de segmentos: e o unico
 * numero desta tela, e ele nao mede nada -- por isso a cor e `tinta`, nao o
 * azul do medido.
 */
export default function NaoEncontrada() {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-5 px-6 py-10">
      <div className="w-full max-w-lg">
        <p className="rotulo-instrumento mb-3">erro de endereço</p>
        <SegmentoLED
          valor="404"
          altura={72}
          cor="tinta"
          rotulo="erro 404, página não encontrada"
          className="mb-5"
        />
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
          <Link href="/dashboard" className={buttonVariants({ size: "sm" })}>
            Ir para a visão geral
          </Link>
          <Link
            href="/dashboard/atendimentos"
            className={buttonVariants({ size: "sm", variant: "outline" })}
          >
            Ver atendimentos
          </Link>
        </div>
      </div>
    </main>
  );
}
