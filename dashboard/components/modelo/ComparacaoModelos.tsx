import type {
  ConjuntoComparado,
  LaudoComparacao,
  MedidasDoModelo,
} from "@/lib/api";
import { comSinal, fracao, milissegundos, pValor, veredito } from "@/lib/comparacao";
import { formatarDataHora, formatarNumero } from "@/lib/formato";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { LIMIAR_SUSPEITO } from "./MetricasTreino";

/**
 * O LAUDO da comparacao BERTimbau x Laya, como o notebook 07 o gravou.
 *
 * Esta tela nao calcula nada: acuracia, F1, matriz, intervalo e o veredito de
 * cada conjunto chegam prontos de `GET /modelo/comparacao`. O que ela decide e
 * o que fica A VISTA -- o placar e a frase da comparacao -- e o que recolhe:
 * VP/FP/FN/VN e a matriz de confusao, que sao sete classes por modelo.
 *
 * Abaixo deste tamanho de conjunto, 100% nao levanta suspeita: a regua de
 * dominio tem 20 frases e acertar todas e possivel sem vazamento nenhum.
 */
const MINIMO_PARA_SUSPEITAR = 100;

export function LaudoDaComparacao({ laudo }: { laudo: LaudoComparacao }) {
  const nomes = laudo.nomes_modelos;
  return (
    <div className="flex min-w-0 flex-col gap-6 px-5 py-4">
      <p className="text-xs leading-relaxed text-muted-foreground">
        Gerado em <span className="num">{formatarDataHora(laudo.gerado_em)}</span>.
        {laudo.rodada_de_fumaca ? (
          <strong className="ml-2 text-warning">
            Rodada de fumaça: o Laya treinou poucos minutos, só para provar o
            caminho. Estes números não são resultado.
          </strong>
        ) : null}
      </p>
      {laudo.ressalvas?.length ? (
        <div className="border border-warning px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-warning">
            Ressalva sobre esta medição
          </p>
          {laudo.ressalvas.map((ressalva) => (
            <p key={ressalva} className="mt-2 max-w-[75ch] text-sm leading-relaxed">
              {ressalva}
            </p>
          ))}
        </div>
      ) : null}
      {laudo.conjuntos.map((conjunto) => (
        <Conjunto key={conjunto.id} conjunto={conjunto} nomes={nomes} />
      ))}
    </div>
  );
}

function Conjunto({
  conjunto,
  nomes,
}: {
  conjunto: ConjuntoComparado;
  nomes: Record<string, string>;
}) {
  const { comparacao } = conjunto;
  const candidato = nomes[comparacao.candidato] ?? comparacao.candidato;
  const referencia = nomes[comparacao.referencia] ?? comparacao.referencia;
  const modelos = Object.entries(conjunto.modelos);

  return (
    <section className="flex min-w-0 flex-col gap-3 border-b border-compasso pb-6 last:border-b-0 last:pb-0">
      <header className="flex min-w-0 flex-col gap-1">
        <h3 className="rotulo-instrumento text-foreground">{conjunto.nome}</h3>
        <p className="text-xs text-muted-foreground">
          <span className="num">{formatarNumero(conjunto.exemplos, 0)}</span> exemplos ·{" "}
          {conjunto.independente
            ? "independente: nenhum modelo viu esta procedência no treino"
            : "mesma procedência do treino"}
          {conjunto.exemplos < MINIMO_PARA_SUSPEITAR
            ? " · amostra pequena: taxa neste conjunto, não acurácia externa"
            : ""}
        </p>
      </header>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Modelo</TableHead>
            <TableHead className="text-right">Acurácia</TableHead>
            <TableHead className="text-right">F1-macro</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {modelos.map(([chave, medidas]) => (
            <TableRow key={chave}>
              <TableCell>{nomes[chave] ?? chave}</TableCell>
              <TableCell className="num text-right text-medido-texto">
                {fracao(medidas.acuracia)}
                {medidas.acuracia >= LIMIAR_SUSPEITO &&
                conjunto.exemplos >= MINIMO_PARA_SUSPEITAR ? (
                  <span className="ml-2 font-sans text-xs text-warning">suspeito</span>
                ) : null}
              </TableCell>
              <TableCell className="num text-right text-medido-texto">
                {fracao(medidas.f1_macro)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <p className="text-sm leading-relaxed">
        <strong>{veredito(comparacao, nomes)}.</strong>{" "}
        <span className="text-muted-foreground">
          {candidato} menos {referencia}:{" "}
          <span className="num text-medido-texto">
            {comSinal(comparacao.diferenca_f1_macro)}
          </span>{" "}
          de F1-macro, IC 95% de{" "}
          <span className="num text-medido-texto">{comSinal(comparacao.ic95[0])}</span> a{" "}
          <span className="num text-medido-texto">{comSinal(comparacao.ic95[1])}</span>.
          McNemar exato: só o {candidato} acerta{" "}
          <span className="num">{formatarNumero(comparacao.mcnemar.so_candidato, 0)}</span>,
          só o {referencia} acerta{" "}
          <span className="num">{formatarNumero(comparacao.mcnemar.so_referencia, 0)}</span>,{" "}
          <span className="num">{pValor(comparacao.mcnemar.p_valor)}</span>.
        </span>
      </p>

      <details className="min-w-0 border border-compasso px-4 py-3">
        <summary className="cursor-pointer text-sm font-medium">
          Verdadeiros e falsos por classe
        </summary>
        <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
          Cada classe contra o resto. VP: era a classe e o modelo disse a classe.
          FP: não era e o modelo disse. FN: era e o modelo disse outra. VN: não
          era e o modelo não disse. Travessão em precisão quer dizer que o
          modelo nunca previu a classe — não há o que medir.
        </p>
        <div className="mt-3 flex min-w-0 flex-col gap-5">
          {modelos.map(([chave, medidas]) => (
            <PorClasse key={chave} nome={nomes[chave] ?? chave} medidas={medidas} />
          ))}
        </div>
      </details>

      <details className="min-w-0 border border-compasso px-4 py-3">
        <summary className="cursor-pointer text-sm font-medium">Matriz de confusão</summary>
        <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
          Linha é a classe real, coluna é a classe que o modelo respondeu. O
          acerto está na diagonal.
        </p>
        <div className="mt-3 flex min-w-0 flex-col gap-5">
          {modelos.map(([chave, medidas]) => (
            <Matriz
              key={chave}
              nome={nomes[chave] ?? chave}
              classes={conjunto.classes}
              matriz={medidas.matriz}
            />
          ))}
        </div>
      </details>
    </section>
  );
}

function PorClasse({ nome, medidas }: { nome: string; medidas: MedidasDoModelo }) {
  return (
    <div className="min-w-0">
      <h4 className="rotulo-instrumento mb-1">{nome}</h4>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Classe</TableHead>
            <TableHead className="text-right">Exemplos</TableHead>
            <TableHead className="text-right">VP</TableHead>
            <TableHead className="text-right">FP</TableHead>
            <TableHead className="text-right">FN</TableHead>
            <TableHead className="text-right">VN</TableHead>
            <TableHead className="text-right">Precisão</TableHead>
            <TableHead className="text-right">Recall</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {medidas.por_classe.map((classe) => (
            <TableRow key={classe.classe}>
              <TableCell>{classe.classe}</TableCell>
              {[classe.exemplos, classe.vp, classe.fp, classe.fn, classe.vn].map(
                (valor, indice) => (
                  <TableCell key={indice} className="num text-right text-medido-texto">
                    {formatarNumero(valor, 0)}
                  </TableCell>
                ),
              )}
              <TableCell className="num text-right text-medido-texto">
                {fracao(classe.precisao)}
              </TableCell>
              <TableCell className="num text-right text-medido-texto">
                {fracao(classe.recall)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function Matriz({
  nome,
  classes,
  matriz,
}: {
  nome: string;
  classes: string[];
  matriz: number[][];
}) {
  return (
    <div className="min-w-0">
      <h4 className="rotulo-instrumento mb-1">{nome}</h4>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Real ↓ · Predito →</TableHead>
            {classes.map((classe) => (
              <TableHead key={classe} className="text-right">
                {classe}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {matriz.map((linha, real) => (
            <TableRow key={classes[real]}>
              <TableHead scope="row">{classes[real]}</TableHead>
              {linha.map((valor, predito) => (
                <TableCell
                  key={classes[predito]}
                  className={
                    real === predito
                      ? "num text-right font-medium text-medido-texto"
                      : "num text-right text-muted-foreground"
                  }
                >
                  {formatarNumero(valor, 0)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function TempoDeResposta({ laudo }: { laudo: LaudoComparacao }) {
  const latencia = laudo.latencia;
  if (!latencia || latencia.medidas.length === 0) return null;
  return (
    <div className="flex min-w-0 flex-col gap-3 px-5 py-4">
      <p className="text-xs leading-relaxed text-muted-foreground">
        Medido em {latencia.hardware}, uma mensagem por vez, em{" "}
        <span className="num">{formatarNumero(latencia.amostra, 0)}</span> mensagens.
      </p>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Modelo</TableHead>
            <TableHead>Tarefa</TableHead>
            <TableHead>Executor</TableHead>
            <TableHead className="text-right">Mediana</TableHead>
            <TableHead className="text-right">p95</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {latencia.medidas.map((medida) => (
            <TableRow key={`${medida.modelo}-${medida.tarefa}-${medida.executor}`}>
              <TableCell>{laudo.nomes_modelos[medida.modelo] ?? medida.modelo}</TableCell>
              <TableCell>{medida.tarefa === "emocao" ? "emoção" : medida.tarefa}</TableCell>
              <TableCell className="num">{medida.executor}</TableCell>
              <TableCell className="num text-right text-medido-texto">
                {milissegundos(medida.mediana_ms)}
              </TableCell>
              <TableCell className="num text-right text-medido-texto">
                {milissegundos(medida.p95_ms)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
