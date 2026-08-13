/**
 * Nota metodologica. Nao e rodape decorativo: e a parte da interface que
 * impede o numero de ser lido como algo que ele nao e.
 */
export function NotaMetodologica({ derivados }: { derivados?: string[] }) {
  return (
    <footer className="quebra-evitar border border-[var(--filete)] bg-[var(--superficie)] px-5 py-4">
      <h2 className="text-[0.8125rem] font-semibold text-[var(--tinta)]">
        Nota metodológica
      </h2>
      <div className="mt-2 grid gap-3 md:grid-cols-2">
        <p className="max-w-[68ch] text-[0.8125rem] leading-[1.6] text-[var(--tinta-2)]">
          <strong className="font-medium text-[var(--tinta)]">
            NPS inferido a partir do texto do atendimento, não de pergunta
            declarada ao cliente. Estimativa.
          </strong>{" "}
          O valor é derivado da fusão de três sinais — texto, emoji e tempo de
          resposta — e convertido para a escala 0–10 antes de cair nas faixas
          canônicas (0–6 detrator, 7–8 neutro, 9–10 promotor). Todo número
          estimado nesta tela carrega{" "}
          <span className="estimado">este sublinhado pontilhado</span>; números
          observados não carregam.
        </p>
        <div className="text-[0.8125rem] leading-[1.6] text-[var(--tinta-2)]">
          <p>
            Atendimento sem fala do cliente aparece como{" "}
            <strong className="font-medium text-[var(--tinta)]">sem sinal</strong>{" "}
            e nunca como nota 0: ausência de dado não é insatisfação.
          </p>
          {derivados && derivados.length > 0 ? (
            <>
              <p className="mt-2">
                Derivado na interface a partir das transcrições, porque a API
                ainda não expõe o agregado:
              </p>
              <ul className="mt-1 list-disc pl-5">
                {derivados.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      </div>
    </footer>
  );
}
