import Link from "next/link";

export default function NaoEncontrado() {
  return (
    <main className="mx-auto flex w-full max-w-[720px] flex-1 flex-col gap-4 px-6 py-16">
      <h1 className="text-[1.25rem] font-semibold text-[var(--tinta)]">
        Atendimento não encontrado
      </h1>
      <p className="max-w-[62ch] text-[0.875rem] leading-[1.6] text-[var(--tinta-2)]">
        A API respondeu 404 para este identificador. Ele pode ter sido removido
        do banco ou o CSV que o continha ainda não foi importado.
      </p>
      <p>
        <Link
          href="/"
          className="text-[0.875rem] text-[var(--tinta-2)] underline underline-offset-[3px] hover:text-[var(--tinta)]"
        >
          ← Todos os atendimentos
        </Link>
      </p>
    </main>
  );
}
