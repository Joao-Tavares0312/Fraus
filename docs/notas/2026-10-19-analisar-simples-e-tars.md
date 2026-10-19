# 19/10/2026 — Analisar simples, menu da conta e TARS

## O que motivou

- Planilha `.xlsx` do TARS deu erro na Analisar: "data ilegível na coluna 'Chat ID'"
  numa tentativa e 500 em outra.
- A Analisar e a navegação estavam complicadas para o cliente final.
- A tela Integrações quase não funcionava em produção.

## Diagnóstico

- O arquivo é lido certo pelo código atual (Papel → autor, Conteúdo → texto,
  Data e hora → data, Chat ID → conversa). O "data ilegível" veio de um
  **mapeamento enviado ou perfil salvo**: perfil vence a inferência.
- O 500 é o incidente de memória de 16/10 (`docs/motores/2026-10-16-incidente.md`,
  SIGKILL em `/analisar/registrar`). O hotfix `580c16d` foi publicado na `fraus-api`
  mas não estava na `main`; este branch o leva.
- Integrações em produção: a importação lia uma pasta do servidor (vazia na Vercel)
  e gerar chave exigia a mestra, que o proxy nunca manda — 403 para o próprio dev.

## O que mudou

1. **Planilha**: a iteração do openpyxl entrou no `try` (nunca mais 500); data de
   célula naive ganha -03:00 na leitura; epoch de 10/13 dígitos conta meia evidência
   de data (um id de chat não empata com a coluna de data); `YYYYMMDD` não é data.
2. **Analisar "arrastar e pronto"**: a prévia devolve `confiavel`
   (`leitura_confiavel` em `fraus/ingest/arquivos.py`). Confiável → analisa e salva
   direto; duvidosa → conferência enxuta (fala e quem falou; o resto recolhido).
   Sempre salva quando há horário; sem horário a leitura é avulsa e a tela diz por quê.
   A UI de perfil salvo saiu da Analisar (as rotas continuam).
3. **Menu da conta**: a lateral tem Visão geral, Atendimentos, Analisar, Grafo e
   Modelo (dev). Operação, Integrações, Configurações, docs, tema e sair foram para
   o menu no rodapé.
4. **Integrações + TARS**: `exigir_mestra_ou_dev` libera chave e segredo de FONTE
   para conta `dev` (chave de acesso continua só com a mestra). A tela ganhou
   "Conectar o TARS"; a importação por pasta saiu da tela.
5. **TARS**: aba Integrações → Fraus (URL + chave cifrada). Depois de cada
   resposta, `after()` manda o atendimento para `POST /ingestao` — reenviar
   substitui. Repescagem pelo botão e pelo cron diário; desliga na 10ª falha
   seguida. (Desenho final do envio no item 7 e em `docs/integracao-tars.md`.)

## Segunda e terceira rodada, testadas em produção

O teste com o Telegram de verdade mostrou dois defeitos, corrigidos no mesmo dia:

6. **O chat inteiro era um atendimento só** — datado de 23/09, numa janela de 40
   mensagens que andava a cada fala. Agora 30 min sem fala encerram o
   atendimento (Tars #29), e o id do atendimento em curso fica em
   `fraus_envios.sessao_id` para sobreviver à poda de 40 mensagens.
7. **A última fala não chegava** — o freio de 1 envio/min deixava duas mensagens
   no mesmo minuto para o cron. Trocado por espera de 5 s: só manda quem ainda
   é a fala mais nova (Tars #30). Conferido pelo João: a conversa inteira chega.
8. **Remover atendimento** (Fraus #98), para limpar o registro de 2243 (id do
   chat lido como horário antes de 02/10) e as duplicatas de teste; e perfil
   salvo que recusa metade das linhas ou mais cede à heurística.

## Pendências

- O id do Tars leva o `chat_id` do Telegram em claro; trocar por hash com sal.
- "Resolveu/Não resolveu" do Tars ainda não vira `feedback_declarado`.
- Retreinar o fusor local em `log1p` (o `fusor.joblib` local é recusado no boot).
