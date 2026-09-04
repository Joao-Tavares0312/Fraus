"use client";

import {
  Children,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { Aparato } from "./Aparato";

/**
 * O APARATO DA TELA -- um, no pe, e nao um por painel.
 *
 * O QUE MUDOU E POR QUE. A §4.1 do DESIGN.md tirou a prosa metodologica de
 * cima do dado e a mandou para o rodape do sistema, e isso funcionou. O que
 * ela nao resolveu: com seis paineis por tela, "Método e ressalvas" passou a
 * aparecer seis vezes, identico, e repeticao le como ruido em vez de rigor.
 *
 * O QUE NAO MUDA: nenhum texto de honestidade sai da tela -- recolher e
 * permitido, remover nao. E os rotulos curtos (`estimativa`, `observado`,
 * `sem sinal`) NAO sao aparato: continuam colados ao numero, sempre visiveis,
 * como a propria §4.1 diz.
 *
 * POR QUE PORTAL, e nao guardar o JSX em estado (primeira versao deste
 * arquivo fazia isso, via `useRegistrarRessalva`): estado copia o `conteudo`
 * no INSTANTE do registro, e o `useEffect` que registra so reroda quando
 * `titulo` muda -- de proposito, para nao entrar em laco quando `conteudo` e
 * JSX recriado a cada render (ver o comentario antigo, ainda valido como
 * explicacao do perigo). O preco dessa guarda era a ressalva CONGELAR: um
 * `FaixaIndicadores` que interpola `indicadores.comSinal` no rodape ficava
 * preso ao primeiro valor, mesmo com o numero mudando na tela ao lado -- texto
 * metodologico divergindo do dado e pior que a repeticao que esta tarefa veio
 * eliminar. Portal resolve isso na raiz: o conteudo nunca sai de dentro da
 * arvore React do painel que o produz, so o DESTINO no DOM e emprestado. Ele
 * re-renderiza quando o painel re-renderiza, porque e filho de verdade dele.
 */

/** O no do DOM onde as ressalvas sao portadas -- o container dentro do `Aparato` da tela. */
const NoContexto = createContext<HTMLElement | null>(null);

/** Setter do no acima, exposto separado para o `AparatoDaTela` nao precisar ler o proprio valor. */
const SetNoContexto = createContext<((no: HTMLElement | null) => void) | null>(
  null,
);

type Inscricao = { registrar: () => void; desregistrar: () => void };

/**
 * So a INSCRICAO (registrar/desregistrar), nao a lista. Quem so registra
 * (`RessalvaDaTela`) nao precisa saber quantos inscritos existem, e as
 * funcoes sao estaveis -- nao disparam o `useEffect` de novo a cada render.
 */
const InscricaoContexto = createContext<Inscricao | null>(null);

/**
 * A CONTAGEM viaja num contexto SEPARADO da inscricao: so o `AparatoDaTela`
 * le isto (para decidir se renderiza o `<Aparato>` ou nao), e cada
 * `RessalvaDaTela` so ESCREVE nela ao montar/desmontar -- se a contagem
 * estivesse no mesmo contexto que a funcao de registrar, toda ressalva
 * re-renderizaria a cada vizinha que entra ou sai.
 */
const ContagemContexto = createContext<number>(0);

export function ProvedorDeAparato({ children }: { children: ReactNode }) {
  const [no, setNoState] = useState<HTMLElement | null>(null);
  const [contagem, setContagem] = useState(0);

  // Guarda contra chamada redundante do ref callback: `setNoState` so muda
  // de fato quando o no muda de IDENTIDADE, nunca a cada render do
  // `AparatoDaTela` -- e o que impede o loop que o brief pediu para evitar.
  const setNo = useCallback((novo: HTMLElement | null) => {
    setNoState((atual) => (atual === novo ? atual : novo));
  }, []);

  const registrar = useCallback(() => setContagem((c) => c + 1), []);
  const desregistrar = useCallback(() => setContagem((c) => c - 1), []);
  const inscricao = useMemo(
    () => ({ registrar, desregistrar }),
    [registrar, desregistrar],
  );

  return (
    <SetNoContexto.Provider value={setNo}>
      <NoContexto.Provider value={no}>
        <InscricaoContexto.Provider value={inscricao}>
          <ContagemContexto.Provider value={contagem}>
            {children}
          </ContagemContexto.Provider>
        </InscricaoContexto.Provider>
      </NoContexto.Provider>
    </SetNoContexto.Provider>
  );
}

/**
 * Montado pelo painel que PRODUZ a ressalva, no lugar do `<Aparato>` que
 * hospedava antes. Fora do provedor os contextos vem `null` e ele vira no-op
 * de proposito: um painel usado solto nao deve quebrar a pagina.
 *
 * `children` vazio (`null`/`undefined`/`false`) nao se inscreve -- e o mesmo
 * caso de "sem legenda nem rodape" que o `Painel` ja tratava antes.
 */
/** Rotulo curto ao lado do titulo, quando o sistema nao produziu dado. */
const ROTULO_DO_ESTADO: Record<"erro" | "vazio", string> = {
  erro: "não carregou",
  vazio: "sem dado",
};

export function RessalvaDaTela({
  titulo,
  /**
   * O painel que produz esta ressalva esta em erro ou vazio -- a mesma
   * precedencia do render do `Painel` (erro vence vazio). AUSENTE no caso
   * normal, de proposito: sem isto o aparato descreveria metodo aplicado a
   * um resultado que nao existe, e a nota metodologica continua verdadeira
   * (o sistema so nao produziu dado desta vez), entao ela nao sai daqui --
   * "recolher e permitido, remover nao". A marcacao e texto, nunca so cor.
   */
  estado,
  children,
}: {
  titulo: string;
  estado?: "erro" | "vazio";
  children?: ReactNode;
}) {
  const no = useContext(NoContexto);
  const inscricao = useContext(InscricaoContexto);
  // `Children.toArray` descarta null/undefined/boolean -- e o jeito correto
  // de perguntar "isto tem conteudo de verdade", diferente de `Boolean(children)`,
  // que e sempre truthy para um array (mesmo `[undefined, undefined]`).
  const temConteudo = Children.toArray(children).length > 0;

  useEffect(() => {
    if (!inscricao || !temConteudo) return;
    inscricao.registrar();
    return () => inscricao.desregistrar();
    // So a PRESENCA de conteudo entra aqui, nao o conteudo em si -- a
    // contagem so precisa saber que existe ressalva, e quem exibe o texto e o
    // portal abaixo, que roda a cada render normal do componente.
  }, [inscricao, temConteudo]);

  if (!no || !temConteudo) return null;

  return createPortal(
    <section>
      <h3 className="mb-1 flex items-baseline gap-2 font-semibold text-foreground">
        {titulo}
        {estado ? (
          <span className="text-xs font-normal text-muted-foreground">
            {ROTULO_DO_ESTADO[estado]}
          </span>
        ) : null}
      </h3>
      {children}
    </section>,
    no,
  );
}

export function AparatoDaTela({ className }: { className?: string }) {
  const setNo = useContext(SetNoContexto);
  const contagem = useContext(ContagemContexto);

  // Callback de ref estavel (setNo nao muda de identidade): o React so chama
  // isto quando o container efetivamente monta ou desmonta, nunca a cada
  // render do `AparatoDaTela`.
  const refContainer = useCallback(
    (no: HTMLDivElement | null) => {
      setNo?.(no);
    },
    [setNo],
  );

  if (contagem === 0) return null;

  return (
    <Aparato className={className}>
      {/*
        Este container fica DENTRO do bloco que o `Aparato` so monta quando
        aberto (ver Aparato.tsx). Isso e seguro porque o `AnimatePresence` de
        la ADIA o desmonte ate a animacao de saida terminar -- o mesmo
        contrato que qualquer outro filho de `Aparato` ja depende. Enquanto
        fechado, nenhuma ressalva portada aqui aparece, o que e o
        comportamento esperado: o aparato comeca recolhido de qualquer jeito.
      */}
      <div
        ref={refContainer}
        className="mt-2 flex max-w-[72ch] flex-col gap-4 text-xs leading-relaxed text-muted-foreground"
      />
    </Aparato>
  );
}
