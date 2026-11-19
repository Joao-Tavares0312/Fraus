# Publicação da API conferida — 19/11/2026

Registro da publicação da API com o artefato conformal (Fraus #119) e do que
foi conferido depois. Dashboard e API são dois deploys; este registro trata da
API.

## O que foi publicado

| Item | Valor |
|---|---|
| Commit da API | `fbccd7f` (merge do #119 na `main`) |
| Como | CLI da Vercel, checkout isolado da `main`, `vercel link --project fraus-api` + `vercel --prod` |
| Deploy | `fraus-cztlkjzgo-wakefull.vercel.app`, alias `fraus-api.vercel.app` |
| Modelos | pacote `42cd90c2…` (inalterado desde 13/11); fusor `5c468660…`, régua `6177f9faef21ec82-1d1e56c8` |
| Artefato novo | `fraus/dados/conformal_fusor.json`, alvo 0,9, mesma régua |

O `api-deploy.yml` foi disparado antes e **falhou** em `vercel pull`: o
ambiente `production-api` não tem `VERCEL_TOKEN` nem os IDs do projeto. Por
isso a publicação foi manual, como em 30/09 e 13/11.

## O que foi conferido

| Rota | Como | Resultado |
|---|---|---|
| `GET /saude` (API direta) | `scripts/smoke_deploy.py` sem token | 200, `status=ok`, `motor=real`, `estado_motor=carregando` (instância fria) |
| `GET /auth/estado` | idem | respondeu JSON |
| `GET /indicadores/confianca` (API direta, sem credencial) | `curl` | 401 — rota existe e exige credencial; **não** prova 200 |
| `GET /indicadores` e `/indicadores/confianca` com credencial | — | **não conferido**: a sessão não tinha a chave de acesso nem um JWT de conta `dev` |

O smoke de contrato (`conferir_contrato`) foi exercitado só com `urlopen`
simulado (`tests/test_operacao_deploy.py`). Contra produção ele precisa de
`FRAUS_SMOKE_TOKEN`; se a chave `FRAUS_CHAVE_ACESSO` não autorizar
`/indicadores`, a conferência fica manual, pelo proxy.

## Pendente, pelo proxy, logado como `dev`

1. `https://<dashboard>/api/fraus/saude` → `status=ok`, `motor=real`.
2. `https://<dashboard>/api/fraus/indicadores` → 200 com
   `feedback_declarado_total` e `concordancia_com_feedback`.
3. `https://<dashboard>/api/fraus/indicadores/confianca` → 200. Um 503 com
   "artefato calibrado para outra régua" quer dizer que o fusor publicado não
   é o `5c468660…`: refazer o passo 1 com o pacote certo.
4. Commit da dashboard publicada e hora da conferência, aqui.
