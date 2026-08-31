import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { Analisador } from "@/components/analisar/Analisador";

export const dynamic = "force-dynamic";

export default function PaginaAnalisar() {
  return (
    <>
      <CabecalhoPagina
        titulo="Analisar um atendimento"
        subtitulo="Envie o arquivo de uma conversa e veja o que o modelo lê nela: a nota, o peso de cada palavra e o vocabulário que essa conversa tem de diferente. Nada disso entra no banco nem mexe nos indicadores."
      />

      <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
        <Analisador />
      </div>
    </>
  );
}
