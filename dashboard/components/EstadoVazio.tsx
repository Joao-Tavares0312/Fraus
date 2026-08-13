/**
 * Estado vazio HONESTO.
 *
 * Este componente e uma posicao de projeto, nao um placeholder: quando a API
 * nao expoe o dado, a dashboard diz o que falta e qual endpoint resolveria, em
 * vez de renderizar um numero plausivel. Numa ferramenta cujo nome vem do
 * daemon do engano, inventar dado seria a pior falha possivel.
 */
export function EstadoVazio({
  titulo,
  explicacao,
  endpoint,
}: {
  titulo: string;
  explicacao: string;
  endpoint?: string;
}) {
  return (
    <div className="flex flex-col items-start gap-2 px-5 py-8">
      <div
        aria-hidden
        className="h-px w-10 bg-[repeating-linear-gradient(90deg,var(--regua)_0_4px,transparent_4px_8px)]"
      />
      <p className="text-[0.875rem] font-semibold text-[var(--tinta)]">{titulo}</p>
      <p className="max-w-[62ch] text-[0.8125rem] leading-[1.55] text-[var(--tinta-2)]">
        {explicacao}
      </p>
      {endpoint ? (
        <p className="text-[0.75rem] text-[var(--tinta-3)]">
          Resolvido por{" "}
          <code className="font-mono text-[var(--tinta-2)]">{endpoint}</code>.
        </p>
      ) : null}
    </div>
  );
}
