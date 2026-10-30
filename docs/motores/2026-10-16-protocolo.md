# Protocolo local — 16/10/2026

Plano aprovado: análise reproduzível e backlog; nenhuma otimização de produção.
Branch local `analise-motores/2026-10-16`; nenhum push ou deploy autorizado.

## Fronteira

- Workspace padrão `/tmp/fraus-analise-20261016`, fora do repositório.
- Subprocessos com ambiente allowlist, HOME/cache temporários e modo offline.
- Não ler `.env*`, credenciais, banco original ou valores de `FRAUS_CHAVE_ACESSO`.
- Não chamar produção, Supabase, Oracle privado, proxy ou Vercel CLI.
- Pesos copiados sem hardlinks/symlinks; joblib não desserializado sem procedência independente.
- Resultados ausentes: `null` e motivo; nunca números simulados.
- Hobby foi informado pelo dono. Região, memória efetiva, build publicado e PAR não verificados.
- `docs/motores/` não está excluído do site público e scripts não estão excluídos do bundle: circulação requer decisão separada. Manter esta branch local.

## Baseline do dono, preservado

Saída inicial de `git status --short`:

```text
 M dashboard/AGENTS.md
 M dashboard/tsconfig.json
?? auditoria-lp/
?? reports/
?? research_notes/
```

Branch inicial `feat/identidade-fr-e-navegacao`. A branch aprovada ainda não existia e foi criada sem descartar mudanças.

## Gates congelados

- ONNX fp32 do mesmo checkpoint: máximo Δp ≤ 0,001; Δscore ≤ 0,01 ponto; zero flips de categoria; informar todo flip de argmax.
- Int8: proposta máximo Δp ≤ 0,02; queda macro-F1 ≤ 0,005 absoluto e zero flips NPS no ouro. Holdout/fusor ausente impede promoção.
- Cinco repetições: igualdade exata e máximo delta separadamente.
- Processo frio não é disco frio. Sem limpeza do cache do SO.
- Warm n=100 por célula, três aquecimentos excluídos, percentis NumPy linear. p99 exploratório.
- Uma célula de benchmark ativa; abortar a 80% da RAM disponível inicial ou 300 s por inferência. Sem encerrar processos do dono.

## Ambiente inicial observado

Consulta de disponibilidade de módulos, sem import de pesos: torch, transformers, onnxruntime, numpy e sklearn disponíveis; onnx, optimum e laya ausentes. A ausência de exportador não autoriza instalar dependências no projeto. Python efetivo observado nos testes: 3.14.7; o projeto declara >=3.11.

## Verificação incremental

TDD dos instrumentos novos: isolamento falhou antes do módulo existir e depois passou (5 casos). Inventário: falha inicial por módulo ausente, evidência integral da sessão `artifact://6`. Artefatos internos da sessão não são caminhos portáveis; resultados finais sanitizados serão copiados para o diretório de evidências do relatório.
