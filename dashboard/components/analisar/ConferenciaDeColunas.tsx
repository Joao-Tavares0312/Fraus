"use client";

import { useId, useState } from "react";
import { Check } from "lucide-react";
import {
  PAPEIS,
  type MapeamentoConfirmado,
  type OrdemData,
  type Papel,
  type PreviaLeitura,
} from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Painel } from "@/components/Painel";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const ROTULO_PAPEL: Record<Papel, string> = {
  texto: "Fala",
  autor: "Quem falou",
  enviada_em: "Data e hora",
  conversa_id: "Conversa",
  canal: "Canal",
};

const EXPLICACAO_PAPEL: Record<Papel, string> = {
  texto: "obrigatório — o que foi dito",
  autor: "obrigatório — cliente, bot ou atendente",
  enviada_em: "sem ela não há latência, logo não há nota",
  conversa_id: "sem ela o arquivo vira uma conversa só",
  canal: "opcional",
};

/** Valor do Select para "este arquivo não tem essa coluna". */
const NENHUMA = "__nenhuma__";

/**
 * A etapa entre escolher o arquivo e analisar: o que o mapeador INFERIU,
 * para o analista conferir antes de o modelo rodar.
 *
 * Existe porque inferência calada é a armadilha da Totalk em escala — uma
 * data MM/DD lida como DD/MM não dá erro, só uma latência absurda. Aqui a
 * inferência vira pergunta com resposta pré-preenchida.
 *
 * O número ao lado de cada papel é a FORÇA DA EVIDÊNCIA da heurística (nome
 * da coluna + conteúdo), não confiança: não é probabilidade calibrada, e
 * chamá-lo de confiança prometeria o que ele não mede.
 */
export function ConferenciaDeColunas({
  previa,
  ocupado,
  nomeArquivo,
  aoAjustar,
  aoConfirmar,
  aoCancelar,
  acao = "analisar",
}: {
  previa: PreviaLeitura;
  /**
   * Na importação, salvar o perfil deixa de ser opcional: é ele que autoriza
   * a coluna inferida a entrar no banco. A análise não grava, então lá lembrar
   * é conveniência.
   */
  acao?: "analisar" | "importar";
  ocupado: boolean;
  nomeArquivo: string;
  aoAjustar: (mapeamento: MapeamentoConfirmado, ordem: OrdemData | null) => void;
  aoConfirmar: (
    mapeamento: MapeamentoConfirmado,
    ordem: OrdemData | null,
    salvarComo: string | null,
  ) => void;
  aoCancelar: () => void;
}) {
  const id = useId();
  const mapa = previa.mapeamento!;
  const escolhido: MapeamentoConfirmado = Object.fromEntries(
    PAPEIS.map((papel) => [papel, mapa.papeis[papel]?.coluna ?? null]),
  );
  const importando = acao === "importar";
  const [lembrarEscolhido, setLembrar] = useState(false);
  const lembrar = importando || lembrarEscolhido;
  const [nomePerfil, setNomePerfil] = useState(
    nomeArquivo.replace(/\.[^.]+$/, "").slice(0, 80),
  );

  const avisosAlemDasColunas = previa.avisos.filter(
    (aviso) => !/^(Colunas (inferidas|confirmadas):|Apliquei o perfil salvo)/.test(aviso),
  );
  const faltaObrigatorio = !escolhido.texto || !escolhido.autor;
  const perguntarOrdem = Boolean(escolhido.enviada_em) && mapa.ordem_data !== null;

  function trocar(papel: Papel, coluna: string | null) {
    const novo: MapeamentoConfirmado = { ...escolhido, [papel]: coluna };
    // Uma coluna faz um papel só: quem a tinha perde.
    if (coluna) {
      for (const outro of PAPEIS) {
        if (outro !== papel && novo[outro] === coluna) novo[outro] = null;
      }
    }
    aoAjustar(novo, mapa.ordem_data);
  }

  const indiceDe = (coluna: string | null | undefined) =>
    coluna ? mapa.colunas.indexOf(coluna) : -1;

  return (
    <Painel
      titulo="Conferir colunas"
      legenda={
        importando
          ? "Este arquivo não está num formato que eu conheça pelo nome, então descobri as colunas pelo nome e pelo conteúdo. Coluna inferida só entra no banco depois de confirmada: ao importar, o mapeamento vira um perfil, e o próximo arquivo com as mesmas colunas entra direto. Nada foi importado ainda."
          : "Este arquivo não está num formato que eu conheça pelo nome, então descobri as colunas pelo nome e pelo conteúdo. Confira antes de analisar: uma coluna errada não dá erro, dá uma nota errada. Nada foi analisado nem gravado ainda."
      }
    >
      {/* `@container`: o painel mora em telas de larguras diferentes — a
          largura inteira em Analisar, meia coluna de 26rem em Integrações.
          A grade responde à largura DELE, não à da janela; com `sm:` ela
          abria duas colunas dentro dos 26rem e o rótulo quebrava letra a letra. */}
      <div className="@container flex flex-col gap-4 px-5 py-4">
        {previa.perfil ? (
          <p className="text-sm text-muted-foreground">
            Apliquei o perfil salvo{" "}
            <strong className="text-foreground">{previa.perfil.nome}</strong>,
            que casa com as colunas deste arquivo.
          </p>
        ) : null}

        <div className="grid gap-3 @xl:grid-cols-2">
          {PAPEIS.map((papel) => {
            const atribuido = mapa.papeis[papel];
            const valor = escolhido[papel] ?? NENHUMA;
            const obrigatorio = papel === "texto" || papel === "autor";
            return (
              <div key={papel} className="flex flex-col gap-1">
                <div className="flex flex-wrap items-baseline gap-x-1.5">
                  <Label htmlFor={`${id}-${papel}`} className="text-sm">
                    {ROTULO_PAPEL[papel]}
                  </Label>
                  <span className="text-xs text-muted-foreground">
                    {EXPLICACAO_PAPEL[papel]}
                  </span>
                </div>
                <Select
                  value={valor}
                  onValueChange={(novo) =>
                    trocar(papel, !novo || novo === NENHUMA ? null : String(novo))
                  }
                  disabled={ocupado}
                >
                  <SelectTrigger
                    id={`${id}-${papel}`}
                    className="h-9 w-full"
                    aria-invalid={obrigatorio && !escolhido[papel] ? true : undefined}
                  >
                    <SelectValue>
                      {(atual: string | null) =>
                        !atual || atual === NENHUMA
                          ? obrigatorio
                            ? "— escolha uma coluna —"
                            : "— o arquivo não tem —"
                          : atual
                      }
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NENHUMA}>
                      {obrigatorio ? "— escolha uma coluna —" : "— o arquivo não tem —"}
                    </SelectItem>
                    {mapa.colunas.map((coluna) => (
                      <SelectItem key={coluna} value={coluna}>
                        {coluna}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {atribuido ? (
                  <span className="text-xs text-muted-foreground">
                    {atribuido.motivo === "confirmado" ? (
                      "confirmado"
                    ) : (
                      <>
                        evidência{" "}
                        <span className="num text-medido-texto">
                          {atribuido.confianca.toLocaleString("pt-BR", {
                            minimumFractionDigits: 2,
                          })}
                        </span>{" "}
                        · {atribuido.motivo}
                      </>
                    )}
                  </span>
                ) : null}
              </div>
            );
          })}
        </div>

        {perguntarOrdem ? (
          <fieldset className="flex flex-col gap-1.5">
            <legend className="text-sm">
              Ordem da data
              {mapa.data_ambigua ? (
                <span className="ml-1.5 text-xs text-warning-rich-text">
                  ambígua — nenhum campo passa de 12
                </span>
              ) : null}
            </legend>
            <div className="flex flex-wrap gap-2">
              {(["dia/mes", "mes/dia"] as const).map((ordem) => (
                <Button
                  key={ordem}
                  type="button"
                  size="sm"
                  variant={mapa.ordem_data === ordem ? "default" : "outline"}
                  aria-pressed={mapa.ordem_data === ordem}
                  disabled={ocupado}
                  onClick={() => aoAjustar(escolhido, ordem)}
                >
                  {ordem === "dia/mes" ? "dia/mês (31/12)" : "mês/dia (12/31)"}
                </Button>
              ))}
            </div>
          </fieldset>
        ) : null}

        {previa.amostra.length > 0 ? (
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-left text-xs">
              <caption className="sr-only">
                Primeiras linhas do arquivo, com dado sensível censurado
              </caption>
              <thead>
                <tr className="border-b border-border">
                  {mapa.colunas.map((coluna, indice) => {
                    const papel = PAPEIS.find((p) => indiceDe(escolhido[p]) === indice);
                    return (
                      <th key={coluna} scope="col" className="px-2.5 py-2 font-medium">
                        <span className="block">{coluna}</span>
                        <span className="block font-normal text-muted-foreground">
                          {papel ? ROTULO_PAPEL[papel] : "ignorada"}
                        </span>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {previa.amostra.map((linha, i) => (
                  <tr key={i} className="border-b border-border last:border-0">
                    {mapa.colunas.map((coluna, indice) => (
                      <td
                        key={coluna}
                        className={
                          indice === indiceDe(escolhido.texto)
                            ? "max-w-72 truncate px-2.5 py-1.5 text-dito-texto"
                            : "max-w-40 truncate px-2.5 py-1.5 text-muted-foreground"
                        }
                        title={linha[indice] ?? ""}
                      >
                        {linha[indice] ?? ""}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        <p className="text-sm text-muted-foreground">
          Com estas colunas:{" "}
          <span className="num text-foreground">{previa.conversas}</span>{" "}
          conversa(s),{" "}
          <span className="num text-foreground">{previa.mensagens}</span>{" "}
          mensagem(ns)
          {previa.total_rejeitadas > 0 ? (
            <>
              ,{" "}
              <span className="num text-foreground">{previa.total_rejeitadas}</span>{" "}
              linha(s) rejeitada(s)
            </>
          ) : null}
          .{!previa.tem_tempo ? " Sem coluna de data: não haverá nota." : null}
        </p>

        {/* A lista de colunas já está nos seletores acima; repeti-la aqui é o
            ruído que a regra 3.7 do handoff proíbe. */}
        {avisosAlemDasColunas.length > 0 ? (
          <Alert>
            <AlertTitle>O que inferi</AlertTitle>
            <AlertDescription>
              <ul className="flex flex-col gap-1">
                {avisosAlemDasColunas.map((aviso) => (
                  <li key={aviso}>{aviso}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        ) : null}

        <div className="flex flex-col gap-2">
          {importando ? (
            <p className="text-sm">
              O mapeamento será salvo como perfil — é o que autoriza estas
              colunas a entrarem no banco.
            </p>
          ) : (
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="size-4 accent-primary"
                checked={lembrar}
                onChange={(evento) => setLembrar(evento.target.checked)}
                disabled={ocupado}
              />
              Lembrar este mapeamento para arquivos com as mesmas colunas
            </label>
          )}
          {lembrar ? (
            <div className="flex flex-col gap-1 sm:max-w-sm">
              <Label htmlFor={`${id}-perfil`} className="text-xs font-normal text-muted-foreground">
                Nome do perfil — grava só os nomes das colunas, nunca o conteúdo
              </Label>
              <Input
                id={`${id}-perfil`}
                value={nomePerfil}
                maxLength={80}
                onChange={(evento) => setNomePerfil(evento.target.value)}
                disabled={ocupado}
              />
            </div>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            onClick={() =>
              aoConfirmar(
                escolhido,
                perguntarOrdem ? mapa.ordem_data : null,
                lembrar && nomePerfil.trim() ? nomePerfil.trim() : null,
              )
            }
            disabled={ocupado || faltaObrigatorio || (importando && !nomePerfil.trim())}
          >
            <Check aria-hidden />
            {importando
              ? ocupado
                ? "Importando…"
                : "Salvar perfil e importar"
              : ocupado
                ? "Analisando…"
                : "Analisar com estas colunas"}
          </Button>
          <Button type="button" variant="outline" onClick={aoCancelar} disabled={ocupado}>
            {importando ? "Cancelar" : "Escolher outro arquivo"}
          </Button>
        </div>
        {faltaObrigatorio ? (
          <p className="text-xs text-warning-rich-text">
            Escolha as colunas de fala e de quem falou para continuar.
          </p>
        ) : null}
      </div>
    </Painel>
  );
}
