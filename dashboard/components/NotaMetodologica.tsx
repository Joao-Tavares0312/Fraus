/**
 * Nota metodologica. Nao e rodape decorativo: e a parte da interface que
 * impede o numero de ser lido como algo que ele nao e.
 */
export function NotaMetodologica({ derivados }: { derivados?: string[] }) {
  return (
    <footer className="quebra-evitar rounded-xl bg-card px-5 py-4 ring-1 ring-foreground/10">
      <h2 className="text-sm font-semibold text-foreground">
        Nota metodológica
      </h2>
      <div className="mt-2 grid gap-4 md:grid-cols-2">
        <div className="max-w-[68ch] text-xs leading-relaxed text-muted-foreground">
          <p>
            <strong className="font-medium text-foreground">
              NPS inferido a partir do texto do atendimento, não de pergunta
              declarada ao cliente. Estimativa.
            </strong>{" "}
            O valor é derivado da fusão de três sinais — texto, emoji e tempo de
            resposta — e convertido para a escala 0–10 antes de cair nas faixas
            canônicas, que a interface lê de{" "}
            <code className="num text-foreground">GET /modelo</code>. Todo
            número estimado carrega{" "}
            <span className="estimado text-foreground">
              este sublinhado pontilhado
            </span>
            ; número observado não carrega.
          </p>
          <p className="mt-2">
            O sinal de tempo é treinado em dados sintéticos calibrados por
            literatura, porque nenhum corpus público de review em português tem
            timestamps de diálogo. Limitação declarada, não escondida.
          </p>
        </div>
        <div className="text-xs leading-relaxed text-muted-foreground">
          <p>
            Atendimento sem fala do cliente aparece como{" "}
            <strong className="font-medium text-foreground">sem sinal</strong> e
            nunca como nota 0: ausência de dado não é insatisfação.
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
