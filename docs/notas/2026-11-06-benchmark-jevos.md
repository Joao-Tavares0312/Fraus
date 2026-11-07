# Benchmark offline do jevos contra o BERTimbau — 06/11/2026

**Pergunta:** o jevos ([feder-cr/jev](https://github.com/feder-cr/jev), release `jevos-v5`,
OpenVINO int8, CPU) é "soberano" contra o BERTimbau do Fraus em satisfação e em ironia?

**Critério, escrito antes de medir:** o jevos só é soberano numa tarefa se, no conjunto
**independente** (ConsumerBR para satisfação, MultiPICo para ironia), o IC95 da diferença de
F1-macro (jevos − BERTimbau) ficar **todo acima de 0**.

**Isto não entra no produto.** O jevos é um LLM; a invariante 1 (sem LLM em runtime) é requisito
do trabalho. Mesmo vencendo, adotá-lo exigiria revogá-la. Nada daqui está em `fraus/` nem em
`pyproject.toml`; o script é `scripts/benchmark_jevos.py` e os JSONs brutos ficam ao lado desta nota.

## Resultado

Cada célula de métrica é acurácia / F1-macro / ECE. Latência é p50/p95 em ms. A diferença é
F1-macro do jevos menos o do BERTimbau, com IC95 por bootstrap pareado (2.000 reamostras).

| Conjunto | Braço | n | BERTimbau | jevos | Diferença F1 [IC95] | Lat. BERTimbau | Lat. jevos |
|---|---|---:|---|---|---|---|---|
| B2W (interno) | cru | 1500 | 0,810 / 0,759 / 0,040 | 0,729 / 0,606 / 0,072 | −0,154 [−0,183, −0,126] | 118/180 | 441/619 |
| B2W (interno) | traduzido | 1500 | 0,810 / 0,759 / 0,040 | 0,746 / 0,615 / 0,067 | −0,144 [−0,175, −0,114] | 119/196 | 435/589 |
| **ConsumerBR (independente)** | cru | 1500 | 0,681 / 0,520 / 0,099 | 0,663 / 0,577 / 0,084 | **+0,057 [+0,027, +0,087]** | 134/270 | 448/924 |
| **ConsumerBR (independente)** | traduzido | 1500 | 0,681 / 0,520 / 0,099 | 0,689 / 0,595 / 0,090 | **+0,075 [+0,044, +0,105]** | 157/321 | 438/765 |
| **MultiPICo-PT (independente)** | cru | 462 | 0,684 / 0,660 / 0,055 | 0,571 / 0,528 / 0,228 | **−0,132 [−0,194, −0,071]** | 114/204 | 105/313 |
| **MultiPICo-PT (independente)** | traduzido | 462 | 0,684 / 0,660 / 0,055 | 0,580 / 0,540 / 0,215 | **−0,120 [−0,183, −0,064]** | 113/208 | 97/285 |
| Régua de 20 frases | cru | 20 | 0,550 / 0,520 / 0,243 | 0,550 / 0,436 / 0,283 | −0,084 [−0,309, +0,110] | 88/99 | 87/95 |
| Régua de 20 frases | traduzido | 20 | 0,550 / 0,520 / 0,243 | 0,650 / 0,601 / 0,281 | +0,081 [−0,227, +0,390] | 85/99 | 82/88 |

## Veredito pela regra

- **Satisfação:** o IC95 no ConsumerBR fica acima de 0 nos dois braços, então a regra literal
  diz que o jevos "vence" ali. Leia isso com as ressalvas abaixo: no B2W, o próprio domínio de
  treino do BERTimbau, ele perde por 0,14–0,15 de F1; o ConsumerBR é o conjunto em que o
  BERTimbau (treinado só em B2W) já está fraco (F1 0,52) e o jevos, que não foi treinado em
  nenhum dos dois, se aproxima. É uma vitória sobre um modelo fora do domínio, não sobre um
  candidato treinado nele.
- **Ironia:** o jevos **perde** no MultiPICo, com o IC95 inteiro abaixo de 0 nos dois braços, e
  com ECE 4 vezes pior (0,22 contra 0,055). Não é soberano em ironia.
- A régua de 20 frases tem IC de ±0,2 e atravessa o zero em todos os casos; não decide nada.

## Conferência de sanidade

O BERTimbau de satisfação foi medido sozinho com a amostra de 5000 do plano e reproduziu os
números publicados em `2026-10-19-benchmark-satisfacao.json` com a mesma impressão de teste:

| Conjunto | acc | F1-macro | impressão |
|---|---|---|---|
| B2W | 0,8200 (pub. 0,82) | 0,7646 (pub. 0,7646) | `481da017399a` (igual) |
| ConsumerBR | 0,6906 (pub. 0,6906) | 0,5388 (pub. 0,5388) | `99a53fd45904` (igual) |

A impressão do MultiPICo (`4eee9c62e8c9`) e a da régua (`90f3ab25892b`) também são iguais às de
19/10. O pipeline de corpora e de BERTimbau está, portanto, inalterado.

## Ressalvas

1. **Amostra de satisfação reduzida de 5000 para 1500.** O plano pedia 5000; a latência medida do
   jevos nesta máquina (8 threads) foi de ~440 ms por pedido de satisfação, e 2 conjuntos × 5000 ×
   2 braços não cabiam. A amostra é estratificada com semente fixa, e por isso a impressão do
   teste mudou (`fe2ef28ce7af`, `c48247ecfb10`) e o F1 do BERTimbau no ConsumerBR cai de 0,539
   (n=5000) para 0,520 (n=1500). A conclusão sobre o jevos usa só números da mesma amostra de 1500.
   Ironia roda completa (462 + 20).
2. **O jevos é documentado como só inglês** ("It reads English only", wiki do jev). O braço
   traduzido (argostranslate pt→en, local) mede o jevos **mais** o tradutor; o BERTimbau sempre lê
   o original em português.
3. **A latência do jevos inclui HTTP e JSON**; a do BERTimbau é `prever_torch` com um texto, em
   processo (4 threads do torch contra 8 do jevos). O jevos publicou 28–130 ms numa máquina de 16
   threads; aqui o pedido de satisfação carrega ~316 tokens (as instruções e os critérios entram
   em todo pedido) e ficou em ~440 ms. Em ironia, o prompt é curto e o jevos empata com o
   BERTimbau em latência (~100 ms).
4. O prompt de satisfação e o de ironia são os fixados no plano, sem ajuste. Outro prompt poderia
   mudar o resultado; não foi explorado, para não ajustar o teste ao candidato.
5. O jevos em repouso consumiu ~94% de uma CPU (giro de threads); o serviço foi parado durante as
   medições do BERTimbau para não contaminar a latência.
6. Procedência: release `jevos-v5` com SHA-256 conferido, `torch_threads = 4`, `jevos threads = 8`,
   `health` e fingerprint do modelo nos JSONs. As respostas cruas do jevos, uma por linha, estão em
   `~/.cache/fraus/experimentos/jevos-2026-11-06/` (fora do git).

## Conclusão

O jevos não é soberano em ironia (perde com folga e calibra mal) e só "vence" em satisfação onde o
BERTimbau está fora do domínio de treino, com ganho de 0,06–0,08 de F1 e 3–4 vezes a latência.
Onde o BERTimbau foi treinado (B2W), o jevos perde por ~0,15. Em nenhum dos casos isso justifica
trocar o motor: a decisão de produto continua sendo a invariante 1.
