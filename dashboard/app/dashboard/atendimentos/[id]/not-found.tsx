import Link from "next/link";
import { EstadoVazio } from "@/components/EstadoVazio";

export default function NaoEncontrado() {
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-10 sm:px-6">
      <h1 className="titulo-instrumento text-lg text-foreground">
        Atendimento não encontrado
      </h1>
      <EstadoVazio
        titulo="Este atendimento não está aqui"
        explicacao="Ele pode ter sido removido ou ainda não ter sido importado."
      />
      <p>
        <Link
          href="/dashboard/atendimentos"
          className="rotulo-instrumento text-primary underline underline-offset-4 hover:text-foreground"
        >
          ← Todos os atendimentos
        </Link>
      </p>
    </div>
  );
}
