import { cabecalhosDaApi, urlDaApi, type Categoria, type IntervaloNps, type Resultado } from "./api";

export type Tema = { id: string; termos: string[]; conversa_ids: string[]; total: number; recentes: number; anteriores: number; taxa_atual: number | null; taxa_anterior: number | null; emergente: boolean; nps: number | null; intervalo: IntervaloNps | null };
export type Radar = { temas: Tema[]; amostra: number; truncadas: number; janela: { de: string; ate: string; base_atual: number; base_anterior: number } | null; metodo?: string };
export type PapelNaEquipe = "proprietario" | "gestor" | "membro";
export type Equipe = { id: string; nome: string; membros: number[]; competencias: string[]; canais: string[]; papeis: Record<string, PapelNaEquipe>; meu_papel?: PapelNaEquipe; integrantes?: { id: number; nome: string; papel: PapelNaEquipe }[] };
export type Turno = { inicio: number; fim: number; pessoas: number; canais: string[] };
export type SimulacaoEscala = { demanda: number; atendidas: number; pendentes: number; espera_mediana_s: number | null; espera_p95_s: number | null; custo: number; dias: { dia: string; demanda: number; atendidas: number; pendentes: number; espera_mediana_s: number | null }[]; previsao: { dia_semana: number; dias_observados: number; contatos_medios: number }[]; metodo: string };
export type Contato = { id: string; canal: string; iniciada_em: string; score: number | null; nota: number | null; categoria: Categoria | null; feedback: number | null };
export type Jornada = { referencia: string; contatos: Contato[]; recontatos: number; canais: string[]; resolucao_declarada: boolean | null };
export type Problema = { id: string; titulo: string; conversa_ids: string[]; equipe_id: string | null; responsavel_id: number | null; prazo: string; termos: string[]; estado: string; acoes: { em: string; ator: string; acao: string; estado: string }[]; medicao: { antes: IntervaloNps | null; depois: IntervaloNps | null; delta_nps: number | null; criterio: string } };
export type PontoReplay = { indice: number; autor: string; texto: string; enviada_em: string; score: number | null; nota: number | null; categoria: Categoria | null; delta: number | null; virada: boolean };
export type Replay = { conversa_id: string; pontos: PontoReplay[]; metodo: string };
export type Cenario = { original: Contato; cenario: Contato; delta_score: number | null; mensagens_cenario: { autor: string; texto: string; enviada_em: string }[]; metodo: string };
export type Comparacao = { resultados: { atual: Contato; candidato: Contato; mudou_categoria: boolean }[]; fatias: { canal: string; n: number; mudaram: number }[]; metodo: string };
export type UsuarioAcesso = { id: number; nome: string; papel: string; ativo: boolean; canais: string[]; configurado: boolean; equipe_id: string | null; exporta_ate: string | null; exportacao_liberada: boolean };
export type Acesso = { usuarios: UsuarioAcesso[]; canais: string[]; equipes: Equipe[]; auditoria: { integra: boolean; total: number; eventos: { ator: string; acao: string; recurso: string; em: string }[]; metodo: string }; modo: string; aviso: string };

/** Teto de `exportar_minutos` em `PUT /operacao/acesso/{id}` (`Politica`, le=480). */
export const TETO_MINUTOS_EXPORTACAO = 480;

/**
 * Quantos minutos faltam para a janela de exportacao de uma conta fechar.
 *
 * Existe porque a rota so sabe receber `exportar_minutos` e grava
 * `exporta_ate: None` quando vem 0 -- ela nao tem como ouvir "nao mexa". O
 * formulario nascia em 0 e sempre enviava o campo, entao editar so os canais
 * de uma conta encerrava a exportacao dela. Reenviar o que RESTA e o mais perto
 * de "nao mexa" que o contrato permite.
 *
 * Arredonda PARA CIMA: o servidor recalcula `agora + minutos`, e arredondar
 * para baixo encurtaria a janela a cada edicao (20 s restantes virariam 0, isto
 * e, revogacao). O custo e o inverso, e e declarado: a janela pode ganhar ate
 * um minuto. `agoraMs` vem por parametro para a funcao continuar pura.
 */
export function minutosRestantesDeExportacao(exportaAte: string | null, agoraMs: number): number {
  if (!exportaAte) return 0;
  const fim = Date.parse(exportaAte);
  if (Number.isNaN(fim) || fim <= agoraMs) return 0;
  return Math.min(TETO_MINUTOS_EXPORTACAO, Math.ceil((fim - agoraMs) / 60_000));
}

export async function consultarOperacao<T>(rota: string, metodo: "GET" | "POST" | "PUT" | "PATCH" = "GET", corpo?: unknown): Promise<Resultado<T>> {
  try {
    const resposta = await fetch(urlDaApi(`/operacao${rota}`), {
      method: metodo, headers: await cabecalhosDaApi(corpo === undefined ? undefined : { "Content-Type": "application/json" }),
      body: corpo === undefined ? undefined : JSON.stringify(corpo), cache: "no-store", signal: AbortSignal.timeout(60_000),
    });
    const dado = await resposta.json();
    if (!resposta.ok) {
      const detalhe = typeof dado.detail === "string" ? dado.detail : Array.isArray(dado.detail) ? dado.detail.map((e: { loc: string[]; msg: string }) => `${e.loc.join(".")}: ${e.msg}`).join("; ") : `A API respondeu ${resposta.status}.`;
      return { ok: false, erro: detalhe };
    }
    return { ok: true, dado: dado as T };
  } catch {
    return { ok: false, erro: "A API não respondeu à consulta da operação. Tente novamente." };
  }
}
