import Link from "next/link";
import { EstadoVazio } from "@/components/EstadoVazio";

export default function NaoEncontrado() {
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-10 sm:px-6">
      <h1 className="text-lg font-semibold text-foreground">
        Atendimento não encontrado
      </h1>
      <EstadoVazio
        titulo="A API respondeu 404 para este identificador"
        explicacao="Ele pode ter sido removido do banco ou o CSV que o continha ainda não foi importado."
        endpoint="GET /conversas/{id}"
      />
      <p>
        <Link
          href="/dashboard/atendimentos"
          className="text-sm text-primary underline underline-offset-4"
        >
          ← Todos os atendimentos
        </Link>
      </p>
    </div>
  );
}
