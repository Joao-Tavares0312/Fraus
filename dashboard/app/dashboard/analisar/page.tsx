import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { Analisador } from "@/components/analisar/Analisador";

export const dynamic = "force-dynamic";

export default function PaginaAnalisar() {
  return (
    <>
      <CabecalhoPagina
        titulo="Analisar um atendimento"
        subtitulo="Analise uma conversa e salve o resultado para acompanhar os indicadores e o grafo. A leitura por mensagem também está disponível em modo avulso."
      />

      <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
        <Analisador />
      </div>
    </>
  );
}
