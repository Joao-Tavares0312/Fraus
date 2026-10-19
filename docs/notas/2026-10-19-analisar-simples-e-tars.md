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
5. **TARS** (`~/GITHUB/tars`, branch `feat/integracao-fraus`): aba Integrações → Fraus
   (URL + chave cifrada). Depois de cada resposta, `after()` manda o chat inteiro para
   `POST /ingestao`, id `tars:<instancia>:<canal>:<chat>` — reenviar substitui.
   Freio de 1 envio/min por chat, repescagem pelo botão e pelo cron diário, desliga
   na 10ª falha seguida.

## Pendências

- Publicar **API e dashboard separadamente** e conferir as rotas pelo proxy.
- Retreinar o fusor local em `log1p` (o `fusor.joblib` local é recusado no boot).
- O TARS de produção precisa do deploy do branch e da chave gerada no Fraus.
