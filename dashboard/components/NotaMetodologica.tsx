import { RessalvaDaTela } from "./AparatoDaTela";

/**
 * Nota metodologica. Nao e rodape decorativo: e a parte da interface que
 * impede o numero de ser lido como algo que ele nao e.
 */
export function NotaMetodologica({ derivados }: { derivados?: string[] }) {
  return (
    // O APARATO GERAL da tela. Perdeu a caixa: no mundo da pauta quem agrupa e
    // regua e espaco, e um cartao aqui deixaria a nota parecendo um aviso
    // avulso em vez do rodape de editor que ela e. A declaracao de honestidade
    // permanece visivel; a procedencia tecnica entra no aparato geral da tela.
    <footer className="quebra-evitar border-t border-linha pt-3">
      <h2 className="text-sm font-semibold text-foreground">
        Nota metodológica
      </h2>
      <div className="mt-2 grid gap-4 md:grid-cols-2">
        <div className="max-w-[68ch] text-sm leading-relaxed text-muted-foreground">
          <p>
            <strong className="font-medium text-foreground">
              NPS inferido a partir do texto do atendimento, não de pergunta
              declarada ao cliente. Estimativa.
            </strong>{" "}
            As notas e categorias vêm do servidor e respeitam as faixas
            vigentes. Todo número estimado carrega{" "}
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
        <div className="text-sm leading-relaxed text-muted-foreground">
          <p>
            Atendimento em que o cliente não falou, ou só usou fórmulas de
            cortesia, aparece como{" "}
            <strong className="font-medium text-foreground">sem sinal</strong> e
            nunca como nota 0: ausência de dado não é insatisfação.
          </p>
        </div>
      </div>
      <RessalvaDaTela titulo="Como os indicadores são calculados">
        <p className="max-w-prose text-sm leading-relaxed text-muted-foreground">A nota combina 39 medidas de sete famílias: texto, emoji, tempo, emoção, léxico, estilo e incongruência. A ironia é lida por mensagem, mas não entra na nota. As faixas vigentes são consultadas em <code>GET /modelo</code>.</p>
        {derivados && derivados.length > 0 ? (
          <>
            <p className="mt-2 text-sm">Consultas que falharam e foram substituídas por cálculos sobre as transcrições disponíveis:</p>
            <ul className="mt-1 list-disc pl-5 text-sm">{derivados.map((item) => <li key={item}>{item}</li>)}</ul>
          </>
        ) : null}
      </RessalvaDaTela>
    </footer>
  );
}
