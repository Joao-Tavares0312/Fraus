import { RessalvaDaTela } from "./AparatoDaTela";

/**
 * Nota metodologica. Nao e rodape decorativo: e a parte da interface que
 * impede o numero de ser lido como algo que ele nao e.
 */
export function NotaMetodologica({ derivados }: { derivados?: string[] }) {
  // KISS (30/10/2026): a nota saiu do pe da tela e mora inteira no aparato
  // ("Método e ressalvas"). Na tela ficam as etiquetas curtas e os ⓘ.
  return (
    <RessalvaDaTela titulo="Nota metodológica">
      <div className="flex max-w-prose flex-col gap-2 text-sm leading-relaxed text-muted-foreground">
        <p>
          <strong className="font-medium text-foreground">
            NPS inferido a partir do texto do atendimento, não de pergunta
            declarada ao cliente. Estimativa.
          </strong>{" "}
          As notas e categorias vêm do servidor e respeitam as faixas vigentes.
          Todo número estimado carrega{" "}
          <span className="estimado text-foreground">este sublinhado pontilhado</span>
          ; número observado não carrega.
        </p>
        <p>
          Atendimento em que o cliente não falou, ou só usou fórmulas de
          cortesia, aparece como{" "}
          <strong className="font-medium text-foreground">sem sinal</strong> e
          nunca como nota 0: ausência de dado não é insatisfação.
        </p>
        <p>
          O sinal de tempo é treinado em dados sintéticos calibrados por
          literatura, porque nenhum corpus público de review em português tem
          timestamps de diálogo. Limitação declarada, não escondida.
        </p>
        <p>
          A nota combina 39 medidas de sete famílias: texto, emoji, tempo,
          emoção, léxico, estilo e incongruência. A ironia é lida por mensagem,
          mas não entra na nota.
        </p>
        {derivados && derivados.length > 0 ? (
          <>
            <p>Consultas que falharam e foram substituídas por cálculos sobre as transcrições disponíveis:</p>
            <ul className="list-disc pl-5">{derivados.map((item) => <li key={item}>{item}</li>)}</ul>
          </>
        ) : null}
      </div>
    </RessalvaDaTela>
  );
}
