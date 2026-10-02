# Operação, análise persistida e produção — 30/09/2026

Referência interna da entrega da PR #75, mesclada na `main` no commit
`ab1b5daad00b4111edb97734bf873c49523bc410`. Registra o contrato entregue e a
validação realizada nesta data. O histórico permanece no
[handoff](../handoff.md); a infraestrutura, em [deploy Vercel](../deploy-vercel.md).

## Estado da publicação

| Unidade | Estado verificado |
|---|---|
| Dashboard `fraus` | build publicado; proxy em `https://fraus-one.vercel.app/api/fraus` |
| API `fraus-api` | deploy `dpl_2ghd1GGyN6ftxYvZ7pgPwnA3KyvF`, estado `Ready`, alias `https://fraus-api.vercel.app` |
| Fonte da API | commit `ab1b5da`, a mesma versão mesclada da entrega |
| Função Python | pacote de **1,95 GB** em `iad1`; tamanho do pacote, não consumo de RAM |
| Banco de produção | PostgreSQL/Supabase, separado das funções efêmeras |

O 404 desta entrega vinha da dashboard nova chamando rotas ausentes na API
antiga. Foi resolvido publicando a API separadamente. **Merge da dashboard não
publica a API.** Uma resposta 200 de `/saude` não comprova que as novas rotas existem.

## Da conversa ao indicador e ao grafo

1. **Analisar** recebe arquivo ou texto e normaliza para `Conversa`.
2. Com salvar marcado, envia multipart a `POST /analisar/registrar`. Horários
   reais são obrigatórios; mapeamento inferido precisa de confirmação.
3. O motor real calcula o score no servidor. Apenas os casos efetivamente
   analisados entram no lote; a entrada não define score ou NPS.
4. `Banco` grava lote e metadados em transação. IDs `analise:` usam a identidade
   do conteúdo para deduplicar reenvios e não sobrescrever outras fontes.
5. A resposta inclui `gravacao` com `salvas`, `ids`, `banco`, `de` e `ate`.
   A interface oferece o período salvo e avisa as outras telas por evento local
   e `localStorage`; atualização também ocorre entre abas e ao voltar o foco.
6. Indicadores, atendimentos e grafo leem o banco com período e escopo de canais
   da sessão. Nenhum agregado é preenchido com mock.

`POST /analisar` e `POST /analisar/arquivo` continuam avulsos, sem gravação.
Motor indisponível é erro explícito; horário ausente ou mapeamento ainda não
confirmado impede persistência. A API real não usa motor de demonstração como fallback.

O NPS é **inferido**, não uma resposta de pesquisa. O cartão respeita
`nps_intervalo.nps = null` abaixo de **30 conversas com sinal**, sem substituir
pelo ponto bruto. AW(3,T) mede incerteza amostral, não erro ou calibração do
modelo. Ausência de score continua sendo “sem sinal”.

Código: `fraus/api/rotas/analise.py`, `fraus/api/registro.py`, `fraus/db.py`,
`fraus/api/escopo.py` e `dashboard/components/analisar/`.

## As sete abas de Operação

As rotas abaixo têm prefixo `/operacao` na API e passam pelo proxy da dashboard.

| Aba | Contratos principais | Comportamento e limites |
|---|---|---|
| Radar | `GET /radar` | TF-IDF/DBSCAN, evidências e taxas dos últimos sete dias versus os sete anteriores; até 1.500 casos recentes |
| Equipe e escala | `GET/POST /equipes`, `PUT /equipes/{id}`, `POST /escala/simular` | equipes persistidas; simulação FCFS por canal, chegadas históricas e hipóteses de turnos, duração e custo |
| Jornadas | `GET/POST /jornadas` | vínculo explícito por referência pseudônima com hash; cronologia e recontatos; resolução somente pelo feedback declarado |
| Investigações | `GET/POST /problemas`, `PATCH /problemas/{id}` | evidências, equipe, responsável, prazo, ações e estado; antes/depois com os mesmos critérios de coorte |
| Replay | `GET /replay/{id}` | estimativa por prefixo sem mensagens futuras, preservando os metadados finais; até 40 mensagens de cliente e 80 no total |
| Laboratório | `POST /laboratorio/cenario`, `POST /laboratorio/comparar` | cópias para limitar espera ou retirar mensagens selecionadas; comparação de até 30 casos e 40 mensagens de cliente por caso |
| Acessos | `GET /acesso`, `PUT /acesso/{usuario_id}`, `POST /acesso/{usuario_id}/revogar-sessoes` | escopo por canal, exportação temporária, sessões e auditoria |

Escala, replay e cenários não regravam a conversa original. Simulação e
comparação antes/depois não demonstram causalidade. Comparar fusores depende
de `FRAUS_FUSOR_CANDIDATO` apontando para um `.joblib` compatível com as **39
features**; não promove o candidato nem repontua o banco. A configuração desse
artefato em produção não foi confirmada nesta entrega.

Código: `fraus/operacao.py`, `fraus/api/rotas/operacao.py` e
`dashboard/components/operacao/`. O padrão visual continua em
`dashboard/DESIGN.md`, incluindo os estados de erro e vazio.

## Hierarquia e convites

Papel global (`dev`/`usuario`) e papel na equipe são independentes. A
administração global conserva seus poderes; aceitar convite nunca concede `dev`.

| Papel na equipe | Permissões de gestão |
|---|---|
| `proprietario` | administra a hierarquia e convida membros ou gestores |
| `gestor` | convida e remove membros; não promove gestores ou proprietários |
| `membro` | participa da equipe; não administra hierarquia ou convites |

- O último proprietário não pode ser removido ou rebaixado.
- Gerar: `POST /equipes/{id}/convites`; validade **1–168 horas**, limite
  **1–100 pessoas**, teto de **100 integrantes** por equipe.
- Listar e revogar: `GET /equipes/{id}/convites` e
  `POST /equipes/{id}/convites/{convite_id}/revogar`.
- O token aleatório é exibido somente na geração; o banco guarda seu hash.
  `/convite/{token}` oferece prévia pública via `GET /convites/{token}`.
- Aceitar: `POST /convites/{token}/aceitar`, com **JWT de usuário**, inclusive
  em desenvolvimento. A credencial técnica não substitui a sessão.
- Cadastro com convite válido pode dispensar o código geral, nasce `usuario`
  e recebe política de canais vazia na mesma transação.
  Desde 02/10/2026 o cadastro também **reserva um uso do convite** nessa
  transação: sem vaga, a conta não nasce (410). Antes o uso só era contado no
  aceite, e um link de limite 1 criava contas sem limite. A reserva não filia;
  `usos` na listagem soma aceites e reservas.
- Aceite valida expiração, revogação, limite, vínculo e concessão de canais
  atomicamente. Quem já integra a equipe não consome outro uso.
- Aceite libera apenas canais explícitos da equipe. Equipe sem canais não
  libera conversas. Remoção ou mudança na equipe recalcula o escopo gerenciado
  por convites e preserva políticas manuais do administrador.
- Contas anteriores sem política conservam o acesso anterior.

Listagem, criação, edição e alteração de papel devolvem a mesma ficha
enriquecida: `integrantes` e `meu_papel` vêm do servidor. A interface não faz
`.map` sobre campo ausente nem deduz permissão administrativa quando recebe
ficha antiga ou incompleta: mostra erro recuperável.

## Persistência, escopo e auditoria

- `operacao_registros(tipo, id, payload, atualizado_em)` persiste registros;
  `auditoria_eventos(id, payload, anterior, assinatura)` guarda a cadeia.
  SQLite usa `BEGIN IMMEDIATE`; PostgreSQL usa trava consultiva nas operações
  concorrentes que exigem exclusão.
- `BancoComEscopo` aplica canais **antes da paginação**, inclusive em detalhe,
  agregado, grafo, referências e gravação. Admin e credencial técnica conservam
  o acesso administrativo previsto no contrato.
- Sessões revalidam usuário ativo, papel e versão do JWT no banco. Revogar
  sessões incrementa a versão e invalida tokens anteriores.
- Exportação temporária: até **480 minutos**. A dashboard autoriza a ação por
  `POST /exportacao/autorizar`; `GET /exportar` gera resumo CSV sem transcrição
  completa e neutraliza fórmulas em células. A política controla a exportação
  do produto, não a cópia de conteúdo visível.
- A cadeia SHA-256 detecta quebra dos vínculos; não é assinatura externa e não
  protege contra reescrita integral do banco por quem o controla.

## Desenvolvimento e QA

Na raiz, com dependências e artefatos reais instalados:

```bash
uv run python -m uvicorn fraus.api.main:app --port 8001 --reload --reload-dir fraus
```

O backend padrão é Torch. Para ONNX, defina `FRAUS_BACKEND=onnx` no ambiente.
A dashboard precisa de `FRAUS_API_URL=http://127.0.0.1:8001` em `.env.local` e
reinício quando essa variável mudar. `scripts/api_demo.py` usa porta 8000 e
dados sintéticos temporários; não é o banco nem a API de produção. MkDocs pode
usar porta 8010.

O 404 local também ocorreu com processo antigo sem reload. Confira porta,
rotas em `/openapi.json` e destino do proxy. No Windows, inicie o supervisor de
reload com `python.exe`; o processo restaurado nesta entrega usa reload.

QA isolado com motor real:

```bash
uv run python scripts/validar_operacao_real.py
uv run python scripts/validar_operacao_real.py --servir --porta 8017
```

O script usa SQLite temporário por padrão. `--postgres` aceita somente banco
local `fraus_validacao`. `dashboard/scripts/validar-operacao-playwright.mjs`
aceita `FRAUS_QA_URL` local (padrão `http://localhost:3017`). `FRAUS_DIST_DIR`
separa o build do Next do servidor habitual. Não use seed ou contas de QA em produção.

## Evidências de validação

| Verificação | Resultado registrado |
|---|---|
| CI da `main`, run `36781395898` | **1.091 passed, 4 skipped, 1 deselected** em cada job, SQLite e PostgreSQL |
| Dashboard | **163 testes em 20 arquivos**, TypeScript, lint dos arquivos alterados e build de produção aprovados |
| API local após correção da ficha de equipe | 16 testes direcionados de Operação e convites aprovados |
| Navegador local, porta 3001 | sete abas sem erro JavaScript; hierarquia visível e edição de equipe com `PUT 200` |
| QA isolado com motor real | gravação, deduplicação, agregado/grafo, replay e cenário exercitados em bancos de validação |
| Produção pelo proxy | radar, equipes, jornadas, problemas e acessos com `200`; escala com `200` e cálculo realizado |
| Saúde e contrato em produção | `/saude`: motor real; `/auth/estado`: login disponível; OpenAPI contém edição, convites, aceite e análise com gravação |

O smoke de produção não criou contas, aceitou convites ou gravou conversas de
teste. Replay e cenários foram exercitados em QA isolado, não neste smoke de
produção. Presença de rota não equivale à validação integral de toda jornada.

## Configuração ainda pendente

Em 30/09/2026, `api-deploy.yml` existe como **workflow manual**. O ambiente
`production-api` não tinha os secrets necessários nem regras de proteção; a
publicação acima foi feita pelo CLI autenticado da Vercel. Falta configurar
`VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `FRAUS_API_PUBLIC_URL` e
`FRAUS_CHAVE_ACESSO` para operar o workflow. Regras de proteção são uma
configuração separada. Não declarar deploy automático da API no merge.

A comparação de fusores exige instalar/configurar o candidato no servidor.
Os limites científicos de ironia, latência sintética e calibração continuam
documentados; a publicação desta entrega não os resolve.
