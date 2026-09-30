import { carregarRecorte } from "@/lib/carregar";
import { sessaoAtual, loginDisponivel } from "@/lib/sessao";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { ConsoleOperacao } from "@/components/operacao/ConsoleOperacao";

export const dynamic = "force-dynamic";

export default async function PaginaOperacao({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const parametros = await searchParams;
  const [recorte, sessao, login] = await Promise.all([carregarRecorte(parametros), sessaoAtual(), loginDisponivel()]);
  const administrador = sessao.estado === "logada" ? sessao.usuario.papel === "dev" : sessao.estado === "ausente" && !login;
  return <>
    <CabecalhoPagina titulo="Operação" subtitulo="Da conversa à ação. Investigue padrões, simule a escala e acompanhe o que mudou com evidências do seu banco." periodo={recorte.periodo} extensao={recorte.extensao} />
    <div className="flex min-w-0 flex-col gap-4 px-4 py-4 sm:px-6">
      {recorte.erro ? <EstadoVazio titulo="Não foi possível carregar a operação" explicacao={recorte.erro} /> :
        <ConsoleOperacao key={recorte.sufixo} conversas={recorte.resumos} sufixo={recorte.sufixo} administrador={administrador} />}
    </div>
  </>;
}
