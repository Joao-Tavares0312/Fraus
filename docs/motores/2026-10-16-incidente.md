# Incidente durante a análise

O dono interrompeu o plano local: pediu investigar a API publicada, aplicar os fixes e não apresentar relatório extenso. Essa autorização substituiu o veto anterior a sondas/deploy **para este incidente**; os demais experimentos continuam locais. Benchmark em andamento foi cancelado, não misturado aos resultados da nova rodada.

## Evidência e ação

- Produção anterior: `dpl_EV4Wy7c2syg6oznbrpnAZbqTNS9A`, commit `0ded4e547e1b38b54ecbfbfcbffd27c92f68c10f`, Ready, iad1, pacote1,95GB, Hobby. Memória8GB mostrada no inspect era **máquina de build**, não função.
- Logs: três500 em `/analisar/registrar` e `Application exited with code137 (SIGKILL)`. LeiturasDB seguiam200. O metadado GET da plataforma não foi tomado como prova do método real do upload.
- Hipótese de memória apoiada por lote de oclusão até61 e carga transitória desnecessária; não há pico da requisição de produção: Observability query respondeu402, exigindo Plus.
- Worktree independente, baseado em origin/main: `hotfix/api-memoria-2026-10-16`. Código limita cada run BERT ONNX a4 sequências e não constrói BERT-ironia se a cabeça selecionada é Laya. Mantidos padding global, truncamento192, ordem/classes, todas as variantes e nulos. Validador do formato do bundle atual continua exigindo os três grafos; isso não obriga carga runtime.
- Prova real local: export de satisfação,61textos de86–194tokens e oclusão; ORT1.30.0, CPU1thread. PicoRSS1.794.387.968→826.523.648bytes, máximoΔp0, zero flips, máximoΔpeso0. Uma cabeça/export local, não memória total de produção.
- TDD:7falhas/4passaram antes;47testes específicos passaram depois. Suíte do worktree:1594passed,5skipped,1deselected. Dois revisores read-only sem bloqueadores. Não alterar fixtures antigas para esconder falhas.
- Commit hotfix `005467f5d2688008b191ac8ee4a0eaf8966f26cb`, cherry-pick local na branch de análise `580c16d`. Nenhum push.
- Deploy isolado, sem alias principal inicialmente: `dpl_AFDn7ikEqCdNQ6ztyYZ3vBGMDb7i`. Build Ready; motor real pronto200 antes da promoção. Depois de promover, API direta e proxy tiveram cold start503/carregando e então200/pronto em16/10às21:35UTC. Artefato e região continuam1,95GB/iad1.

## Limite da verificação autenticada

Credencial técnica local foi recusada401; credencial produção marcada sensitive não é legível pela API Vercel. Relay do navegador indisponível. OpenAPI da candidata pediu credencial; não foi confundido com ausência de rotas. Não houve upload/gravação de conversa, criação de usuário, alteração de modelo, Supabase direto, relaxamento de autenticação ou impressão de segredos. O upload autenticado que originou o incidente não foi repetido pelo assistente; sua resolução ponta a ponta não está comprovada apenas por saúde pronta.

A análise original mantém seus bloqueios de fusor/ONNX/Laya. A rodada de desempenho posterior é independente do benchmark interrompido; registrar suas condições e não extrapolar estes números locais para a função publicada.
