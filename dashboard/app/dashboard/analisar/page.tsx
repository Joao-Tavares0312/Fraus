import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { Analisador } from "@/components/analisar/Analisador";

export const dynamic = "force-dynamic";

export default function PaginaAnalisar() {
  return (
    <>
      <CabecalhoPagina
        titulo="Analisar um atendimento"
        subtitulo="Solte o arquivo da conversa: o Fraus lê cada mensagem, estima a satisfação e soma aos indicadores."
      />

      <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
        <Analisador />
      </div>
    </>
  );
}
