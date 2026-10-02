import {
  ArrowLeftRight,
  ArrowUpRight,
  Check,
  ChevronLeft,
  ChevronRight,
  ChevronsUpDown,
  Copy,
  Link2,
  LogIn,
  LogOut,
  Pencil,
  Play,
  Plus,
  Power,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Trash2,
  Upload,
  X,
  type LucideIcon,
} from "lucide-react";

/**
 * UM VERBO, UM DESENHO.
 *
 * O botão de ação carrega o ícone do VERBO, não o do assunto: "Salvar faixas"
 * e "Salvar equipe" são a mesma ação e levam o mesmo desenho, e é isso que
 * deixa o olho achar "salvar" numa tela nova sem ler. O mapa mora num lugar só
 * para que ninguém escolha um segundo ícone para um verbo que já tem um.
 *
 * Só AÇÃO entra aqui. Controle de seleção (as abas de perfil, a ordem de data,
 * a linha clicável de uma lista) não leva ícone de verbo: ele não faz nada,
 * ele escolhe, e o estado escolhido já é dito por `aria-pressed` e pelo fundo.
 *
 * O ícone é sempre decorativo (`aria-hidden`): o nome do botão é o texto.
 */
export const ICONES_DE_ACAO = {
  salvar: Save,
  /** Confirma o que está na tela: aplicar, aceitar, "sim", "já copiei". */
  confirmar: Check,
  /** Desiste sem efeito: cancelar, "não", manter, limpar a busca. */
  cancelar: X,
  /** Apaga ou revoga — o que não volta. */
  remover: Trash2,
  copiar: Copy,
  /** Faz nascer: criar, adicionar, gerar, registrar. */
  criar: Plus,
  /** Busca de novo o mesmo dado. */
  atualizar: RefreshCw,
  /** Volta a um estado anterior conhecido. */
  restaurar: RotateCcw,
  editar: Pencil,
  buscar: Search,
  /** Roda o modelo ou uma simulação sobre o que foi informado. */
  executar: Play,
  /** Leva a outra tela ou abre um registro novo a partir deste. */
  abrir: ArrowUpRight,
  arquivo: Upload,
  anterior: ChevronLeft,
  proxima: ChevronRight,
  /** Troca a FORMA de ver o mesmo dado (gráfico ↔ tabela). */
  alternar: ArrowLeftRight,
  expandir: ChevronsUpDown,
  vincular: Link2,
  entrar: LogIn,
  /** Encerra sessão. */
  sair: LogOut,
  /** Liga ou desliga algo que continua existindo. */
  ligar: Power,
} as const satisfies Record<string, LucideIcon>;

export type AcaoComIcone = keyof typeof ICONES_DE_ACAO;

export function IconeDeAcao({ acao }: { acao: AcaoComIcone }) {
  const Icone = ICONES_DE_ACAO[acao];
  return <Icone aria-hidden />;
}
