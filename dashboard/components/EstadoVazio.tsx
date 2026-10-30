import { Files } from "lucide-react";
import { ehFalhaDeConexao } from "@/lib/api";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { cn } from "@/lib/utils";
import { RessalvaDaTela } from "./AparatoDaTela";

/**
 * Estado vazio HONESTO.
 *
 * Este componente e uma posicao de projeto, nao um placeholder: quando a API
 * nao expoe o dado, a dashboard diz o que falta e qual endpoint ou etapa
 * resolveria, em vez de renderizar um numero plausivel. Numa ferramenta cujo
 * nome vem do daemon do engano, inventar dado seria a pior falha possivel.
 *
 * Ele e tambem o modo de FALHA ISOLADA: um painel que nao carrega mostra o
 * proprio erro aqui dentro e os vizinhos continuam de pe.
 *
 * QUANDO A CAUSA E A API FORA DO AR, ele fala menos. A regua no topo da tela ja
 * anuncia o estado e carrega a acao; um paragrafo por painel repetindo a mesma
 * instrucao nao reforca nada -- so empurra o resto da tela para baixo, tres,
 * quatro vezes na mesma pagina. A prosa metodologica NAO e removida: ela recolhe
 * para aparato (DESIGN.md 4.1), porque recolher e permitido e remover nao.
 */
export function EstadoVazio({
  titulo,
  explicacao,
  endpoint,
  etapa,
  className,
}: {
  titulo: string;
  /** Opcional: um titulo que ja se explica nao paga uma segunda frase. */
  explicacao?: string;
  /** Rota que passaria a devolver este dado, quando houver. */
  endpoint?: string;
  /** Etapa do projeto que falta rodar, quando o que falta nao e uma rota. */
  etapa?: string;
  className?: string;
}) {
  const apiFora = explicacao ? ehFalhaDeConexao(explicacao) : false;

  // A primeira frase é a marca ("API não respondeu em …"), que a régua do topo
  // já diz melhor. O resto é a prosa metodológica, e ela sobrevive no aparato.
  const aparato = apiFora && explicacao
    ? explicacao.slice(explicacao.indexOf(". ") + 1).trim()
    : "";

  return (
    <Empty
      className={cn(
        "items-start border-0 text-left",
        // O `Empty` do chassi tem `flex-1` e estica para preencher a coluna da
        // pagina. Com a prosa recolhida, isso virava uma moldura tracejada de
        // meia tela em volta de duas linhas de texto -- desperdicio que parece
        // defeito. Falha de conexao ocupa a altura do que tem a dizer; os
        // outros vazios continuam preenchendo a area do painel que substituem
        // (o do grafico, por exemplo, precisa da altura do grafico).
        apiFora && "flex-none py-8",
        className,
      )}
    >
      <EmptyHeader className="max-w-[62ch] items-start text-left">
        <EmptyMedia variant="icon" className="mb-1 bg-transparent text-muted-foreground">
          <Files aria-hidden />
        </EmptyMedia>
        <EmptyTitle className="text-base text-foreground">{titulo}</EmptyTitle>

        {apiFora ? (
          <EmptyDescription className="text-sm leading-relaxed">
            Sem dado enquanto a API não responde — a ação está na faixa no topo
            da tela.
          </EmptyDescription>
        ) : explicacao ? (
          <EmptyDescription className="text-sm leading-relaxed">{explicacao}</EmptyDescription>
        ) : null}

        {etapa ? (
          <EmptyDescription className="text-sm leading-relaxed">
            Próximo passo: <span className="text-foreground">{etapa}</span>.
          </EmptyDescription>
        ) : null}

        {endpoint || (apiFora && aparato) ? (
          <RessalvaDaTela titulo={titulo} estado={apiFora ? "erro" : "vazio"}>
            {endpoint ? <p className="text-sm leading-relaxed">Origem dos dados: <code>{endpoint}</code>.</p> : null}
            {apiFora && aparato ? <p className="mt-1.5 max-w-[62ch] text-sm leading-relaxed text-muted-foreground">{aparato}</p> : null}
          </RessalvaDaTela>
        ) : null}
      </EmptyHeader>
    </Empty>
  );
}
