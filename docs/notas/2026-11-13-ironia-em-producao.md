# Ironia do MultiPICo em produção e o candidato 42 no fusor — 13/11/2026

Duas medições e uma publicação. Nenhuma nota, categoria ou NPS mudou: a ironia
não entra no vetor do fusor, e o fusor e as cabeças de satisfação e emoção do
pacote novo são os mesmos bytes do pacote anterior.

## O que estava em produção

O ZIP `modelos-vercel-d645bcc4.zip`, de 17/09/2026, com a cabeça de ironia de
agosto treinada no IDPT, em ONNX int8. Nem a cabeça do MultiPICo (19/10) nem
outro artefato tinha sido enviado desde então. O fusor desse ZIP é o de 15/09,
já em `log1p`; o artefato em segundos crus era só a cópia local.

## Ironia: produção contra MultiPICo, nos artefatos ONNX exatos

JSON bruto em `2026-11-13-benchmark-ironia-onnx.json`. Mesma impressão de teste
de 19/10 (`4eee9c62e8c9` e `90f3ab25892b`).

| Conjunto | n | Produção (IDPT, int8) | MultiPICo (fp32) | Diferença de F1-macro [IC95] |
|---|---:|---|---|---|
| MultiPICo-PT, teste | 462 | F1 0,490 · ECE 0,361 | F1 0,660 · ECE 0,055 | +0,170 [+0,111; +0,227] |
| Régua de 20 frases | 20 | F1 0,437 | F1 0,520 | +0,083 [−0,252; +0,398] |

Ressalvas: o teste do MultiPICo é do mesmo corpus em que a cabeça nova foi
treinada (divisão por post), portanto teste interno para ela; a régua de 20
frases não decide. A cabeça continua pouco confiável em frase de suporte:
"Nossa, que atendimento maravilhoso, só esperei três horas" sai com 0,16.

A exportação para ONNX fp32 teve paridade Δp 0,0000 (`encolher_modelos.py
--so ironia --precisao fp32`).

## Publicação

- Pacote `modelos-vercel-2026-11-13-42cd90c2.zip`, 1.214.004.228 bytes,
  SHA-256 `42cd90c28792bd171c364b32ef241228a377d9ddaf7837a08baab0b2d31af539`.
- Preview conferido antes da troca: build, `/saude/prontidao` em 200, seis
  simulações e três análises avulsas de 40 mensagens de cliente, sem falha.
- Produção: deploy `dpl_jNR5nb9q3DxPVyz3Hx7afaif2d9s`, da `main` em `2daf4c1`.
  Prontidão em 200 cerca de 25 s depois da primeira sonda; três simulações em
  200 com os mesmos valores de ironia do ONNX local.
- Memória: o pico local com as três cabeças subiu de 1.957 MB para 2.501 MB.
  É medida de estação de trabalho, não da função. Na Vercel não houve estouro
  nos testes acima; carga sustentada não foi medida.

Volta: o ZIP anterior continua no bucket (SHA-256
`d645bcc40c924921ff578f4237e8f7b80bf9b5840e9d7a71da2be37f4f3c21a4`). Restaurar
`FRAUS_MODELOS_URL` e `FRAUS_MODELOS_SHA256` e publicar de novo.

## Satisfação: o candidato 42 não foi promovido

O candidato 42 (campanha T4 de 26/10) vence no ConsumerBR: 0,573 contra 0,539,
diferença +0,035 [+0,019; +0,049] (`2026-10-29-benchmark-satisfacao.json`).
Em 13/11 ele foi medido dentro do fusor, com o mesmo manifesto e as mesmas 300
conversas sintéticas de teste:

| | Cabeça atual | Candidato 42 |
|---|---:|---:|
| Fusor completo, F1-macro | 0,940 | 0,911 |
| Só as 4 features de texto, F1-macro | 0,940 | 0,880 |
| Recall de neutro | 0,91 | 0,76 |
| ECE | 0,020 | 0,043 |

Diferença pareada de F1 (42 − atual): −0,029 [−0,064; +0,005]. O intervalo
cruza o zero. A comparação favorece a cabeça atual, que pode ter visto frases
desse teste na divisão antiga do B2W; o candidato comprovadamente não viu (os
três fingerprints da divisão batem com o manifesto). A queda no neutro repete a
do ConsumerBR (recall 0,37 → 0,16) e pesa no produto, porque neutro é a faixa
7–8 do NPS. Decisão: não promover antes de um ajuste que recupere o neutro.

Os pesos do candidato 42 estão em `~/.cache/fraus/candidatos/satisfacao-42`
(SHA-256 `709951b5…`); os dois fusores e os caches de features, em
`~/.cache/fraus/promocao-2026-11-13/`. Fora do git.
