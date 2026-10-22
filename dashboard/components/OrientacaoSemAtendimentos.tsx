import Link from "next/link";
import { ArrowUpFromLine, Cable, CalendarRange } from "lucide-react";
import { sessaoAtual, estadoAutenticacao } from "@/lib/sessao";
import { Painel } from "@/components/Painel";
import { buttonVariants } from "@/components/ui/button";
import type { Extensao } from "@/lib/periodo";

/** Só aparece depois de a listagem confirmar que o recorte está vazio. */
export async function OrientacaoSemAtendimentos({ extensao, caminho }: {
  extensao: Extensao;
  caminho: "/dashboard" | "/dashboard/atendimentos";
}) {
  if (extensao) {
    return (
      <Painel titulo="Nenhum atendimento neste período" nivel="dominante">
        <div className="flex max-w-prose flex-col items-start gap-5 py-2">
          <p className="text-base leading-relaxed text-muted-foreground">Há atendimentos em outros dias. Limpe o período para voltar a vê-los ou escolha outras datas no filtro acima.</p>
          <Link href={caminho} className={`${buttonVariants({ size: "lg" })} min-h-10 text-sm`}>
            <CalendarRange aria-hidden />Limpar período
          </Link>
        </div>
      </Painel>
    );
  }

  const sessao = await sessaoAtual();
  const podeConfigurar = sessao.estado === "logada"
    ? sessao.usuario.papel === "dev"
    : sessao.estado === "ausente" && (await estadoAutenticacao()).estado === "desativado";

  return (
    <Painel titulo="Comece pelo seu primeiro atendimento" nivel="dominante">
      <div className="flex max-w-prose flex-col gap-5 py-2">
        <p className="text-base leading-relaxed text-muted-foreground">
          Ainda não há atendimentos disponíveis. Analise um arquivo para conhecer a leitura do Fraus{podeConfigurar ? " ou conecte uma fonte para receber novas conversas." : "."}
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/dashboard/analisar" className={`${buttonVariants({ size: "lg" })} min-h-10 whitespace-normal text-sm`}>
            <ArrowUpFromLine aria-hidden />Analisar meu primeiro arquivo
          </Link>
          {podeConfigurar ? (
            <Link href="/dashboard/integracoes" className={`${buttonVariants({ size: "lg", variant: "outline" })} min-h-10 text-sm`}>
              <Cable aria-hidden />Conectar uma fonte
            </Link>
          ) : null}
        </div>
        <p className="text-sm leading-relaxed text-muted-foreground">Com horários nas mensagens, a análise pode ser salva nos indicadores. Sem horários, você pode ler a análise por mensagem, mas não gerar nota nem salvar nos indicadores.</p>
      </div>
    </Painel>
  );
}
