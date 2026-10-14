# Specs e planos: índice de status

O diário de decisão do projeto. Nada aqui se apaga, porque cada spec registra
alternativas recusadas e o motivo. Este índice diz **o que ainda vale**.

Como o status foi medido (limpeza de 14/10/2026): nenhum plano marca
checkbox, então a conclusão foi conferida pela **existência na `main` dos
arquivos que o plano manda criar**, não pelos testes de cada um. Caminhos
que mudaram depois (`app/<x>` → `app/dashboard/<x>`, `/leitura` → `/`) contam
como concluídos.

## Em andamento

| spec | plano | assunto |
|---|---|---|
| `specs/2026-10-08-regua-pares-ironia-design.md` | `plans/2026-10-08-regua-pares-ironia.md` | régua de pares mínimos de ironia; anotação às cegas em curso (`docs/ironia.md`). A página de anotação do passo 5 do plano foi substituída pela rota `/anotar` e saiu do repositório em 14/10 |
| `specs/2026-10-14-diferenciais-visao-geral.md` e `specs/2026-10-14-e1…e6-*` | `plans/2026-10-14-diferenciais.md` | diferenciais medidos (explicação exata, calibração/conformal, declarado × inferido, benchmark × LLM, sinalizadores, tema e deterioração); **aguardando aprovação** |

## Concluídos e vigentes

| spec | plano | assunto |
|---|---|---|
| `specs/2026-08-13-dolos-design.md` | `plans/2026-08-13-dolos-implementacao.md` | o projeto inteiro (referência principal, citada no `CLAUDE.md`) |
| `specs/2026-08-14-autenticacao-design.md` | `plans/2026-08-14-autenticacao.md` | autenticação |
| `specs/2026-08-17-api-modular-design.md` | `plans/2026-08-17-api-modular.md` | rotas em `fraus/api/rotas/` |
| `specs/2026-08-17-chave-mestra-por-botao-design.md` | `plans/2026-08-17-chave-mestra-por-botao.md` | chave mestra pela dashboard |
| `specs/2026-08-18-subir-a-api-pela-dashboard-design.md` | — | subir a API pela dashboard |
| `specs/2026-08-19-grafo-memoria-design.md` | `plans/2026-08-19-grafo-da-memoria.md` | grafo |
| `specs/2026-08-20-nps-neutro-alinhado-design.md` | — | peso do neutro no score |
| `specs/2026-08-21-sinal-de-estilo-e-contrato-completo-design.md` | `plans/2026-08-21-sinal-de-estilo-e-contrato-completo.md` | sinal de estilo |
| `specs/2026-08-25-lexico-curado-design.md` | `plans/2026-08-25-lexico-curado.md` | curadoria do léxico |
| `specs/2026-08-27-webhook-integracao-design.md` | `plans/2026-08-27-webhook-integracao.md` | webhook assinado |
| `specs/2026-08-31-lp-e-autenticacao-design.md` | `plans/2026-08-31-lp-e-autenticacao.md` | LP e login |
| `specs/2026-09-03-censura-pii-design.md` | `plans/2026-09-03-ironia-estilo-e-pii.md` | censura de PII |
| `specs/2026-09-03-leitura-de-estilo-design.md` | (mesmo plano) | leitura de estilo |
| `specs/2026-09-03-incongruencia-ironia-design.md`, `specs/2026-09-03-incongruencia-bibliografia.md`, `specs/2026-09-04-incongruencia-implicita-design.md` | — | família `incongruencia_*` |
| `specs/2026-09-08-abstencao-por-contestacao-design.md` | — | abstenção por contestação |
| `specs/2026-09-30-instrumento-design.md` | — | o mundo visual vigente (Instrumento) |
| `specs/2026-10-09-lp-nova-vgpu-design.md` | `plans/2026-10-09-lp-nova-vgpu.md` | LP em vgpu. **Desfecho:** a LP virou a raiz `/` e `/leitura` só redireciona (`next.config.ts`); o texto da spec que fala em `/leitura` e em "vitrine de `/` intocada" é anterior a isso |

## Substituídos pelo Instrumento (30/09/2026)

Mundos visuais anteriores. Valem como história de decisão, não como guia de
interface; o guia é `dashboard/DESIGN.md`.

| spec | plano |
|---|---|
| `specs/2026-08-21-vidro-liquido-design.md` | `plans/2026-08-21-vidro-liquido-implementacao.md` |
| `specs/2026-08-24-vaporwave-design.md` | `plans/2026-08-24-vaporwave-implementacao.md` |
| `specs/2026-08-25-a-fenda-design.md` | `plans/2026-08-25-a-fenda.md` |
| `specs/2026-08-31-pauta-evoluido-design.md` | — |
| `specs/2026-09-04-tipografia-e-heroi-design.md` | `plans/2026-09-04-tipografia-e-heroi.md` |
| `specs/2026-09-04-hierarquia-e-vitrine-design.md` | `plans/2026-09-04-hierarquia-e-vitrine.md` |
