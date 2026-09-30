# Fraus — instruções do projeto

Ferramenta de IA que analisa atendimentos de chatbot e mede satisfação do cliente
**sem LLM em runtime**. Trabalho acadêmico, será apresentado numa banca.

> **Sessão nova? Leia [docs/handoff.md](docs/handoff.md) primeiro.** Ele traz o
> estado atual, as regras que governam este código com o motivo de cada uma
> (várias parecem erro até você saber por que existem), as pendências em ordem
> e as armadilhas já pagas. Para trabalho de interface, `dashboard/DESIGN.md` e
> `dashboard/PRODUCT.md` são obrigatórios.

---

## Arquitetura em uma tela

```
CSV / Discord / WhatsApp
        ↓  adapter de ingestão (fraus/ingest/)
   Conversa  ← modelo canônico único (fraus/modelos.py)
        ↓
 ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
 │texto    │emoji    │tempo    │emoção   │léxico   │ironia   │estilo   │incongru-│
 │BERTimbau│lexicon  │latência │7 clas-  │SentiLex │cabeça   │caixa    │ência    │
 │por      │+ posi-  │escala-  │ses +    │-PT02 +  │binária  │alta +   │emoji×   │
 │mensagem │ção      │ção      │desprezo │negação  │(*)      │palavrão │texto    │
 └────┬────┴────┬────┴────┬────┴────┬────┴────┬────┴─────────┴────┬────┴────┬────┘
            ↓  39 features                                     (*) por mensagem,
      Fusor (LogisticRegression + StandardScaler)                   direto p/ dashboard
            ↓  score 0–100
   nota 0–10 → categoria NPS → indicadores agregados
            ↓
      FastAPI  →  dashboard Next.js
```

(*) A cabeça de ironia continua carregada, obrigatória e lida por mensagem,
mas desde 04/09/2026 **não entra no vetor do Fusor** — medida no próprio
corpus de treino, ela funciona como detector de sentimento positivo, não de
ironia (ver `fraus/fusor.py`, comentário de `NOMES_FEATURES`, e
`docs/treinamento.md`).

## Mapa de arquivos

| Caminho | Responsabilidade |
|---|---|
| `fraus/modelos.py` | `Conversa` / `Mensagem` — modelo canônico |
| `fraus/ingest/csv_driver.py` | CSV → conversas, isolando linha malformada |
| `fraus/ingest/simulador.py` | conversas sintéticas determinísticas (treino do sinal de tempo) |
| `fraus/sinais/texto.py` | BERTimbau, probabilidade **por mensagem** (torch importado só se usado) |
| `fraus/sinais/onnx.py` | o mesmo checkpoint no ONNX Runtime — `FRAUS_BACKEND=onnx`, ver `docs/encolhimento.md` |
| `fraus/sinais/emoji.py` | lexicon + posição relativa |
| `fraus/sinais/tempo.py` | latência, escalação, abandono |
| `fraus/sinais/emocao.py` | 7 classes de emoção; desprezo derivado da díade raiva+nojo |
| `fraus/sinais/lexico.py` | SentiLex-PT02 + escopo de negação |
| `fraus/sinais/ironia.py` | cabeça binária (IDPT 2021) |
| `fraus/sinais/estilo.py` | caixa alta, pontuação, alongamento, palavrão, censura |
| `fraus/sinais/curadoria.py` | o que o analista ensinou ao léxico — vence o SentiLex e o ranking de emoji |
| `fraus/cortesia.py` | "ok, obrigado" sozinho é **sem sinal**, não promotor — `Conversa.tem_sinal_cliente` |
| `fraus/fatias.py` | avaliação por fatia (parte pura); `scripts/avaliar_por_fatias.py` alimenta `docs/cartao-do-modelo.md` |
| `fraus/api/repontuacao.py` | repontuar em segundo plano, com progresso e 409 se já rodando |
| `scripts/retreinar_fusor_local.py` | reproduz o notebook 02 em CPU e só grava o fusor com `--promover` |
| `fraus/api/rotas/lexico.py` | cadastrar, listar e revogar termo curado |
| `fraus/assinatura.py` | HMAC do webhook — o segredo mora no ambiente, nunca no banco |
| `fraus/api/vazao.py` | dois tetos: `/auth/*` por IP em middleware, `/ingestao` por fonte na rota |
| `fraus/api/registro.py` | o miolo de derivação, compartilhado pelas duas rotas de entrada |
| `fraus/api/rotas/webhook.py` | webhook assinado por fonte, com registro de entrega |
| `scripts/preparar_sentilex.py` | converte o SentiLex bruto em `fraus/dados/sentilex_pt02.csv` |
| `fraus/fusor.py` | `NOMES_FEATURES` (39) e o `Fusor` |
| `fraus/indicadores.py` | NPS, CSAT, containment, nota, categoria |
| `fraus/configuracao.py` | configuração vigente: padrão de fábrica no código, delta no banco |
| `fraus/db.py` | PostgreSQL/Supabase em produção, SQLite local; lotes e metadados transacionais, sem ORM |
| `fraus/operacao.py` | temas, simulação de escala e cópia de cenários; nenhuma promoção de modelo |
| `fraus/api/rotas/operacao.py` | equipes, convites, jornadas, investigações, replay, laboratório, acessos e exportação |
| `fraus/api/escopo.py` | `BancoComEscopo`: canais autorizados antes de listar, agregar, consultar ou gravar |
| `fraus/api/rotas/analise.py` | análise avulsa e `POST /analisar/registrar`, que salva apenas o lote analisado |
| `fraus/api/main.py` | FastAPI: `criar_app` (fábrica) e `app` (lazy, PEP 562) |
| `fraus/evidencia.py` | evidência fraca (a cabeça tracejada) — observável, nunca probabilidade |
| `fraus/deriva.py` | deriva de distribuição — a invariante 10 como alarme de runtime |
| `dashboard/` | Next.js — ver `dashboard/DESIGN.md` |
| `notebooks/` | treino no Colab (BERTimbau, depois fusor) |
| `scripts/api_demo.py` | snapshot sintético temporário; motor real se houver artefatos, dublê explícito caso contrário — **nunca em produção** |
| `scripts/validar_operacao_real.py` | QA com ONNX real e banco temporário ou PostgreSQL local de validação |

## Estado operacional — 30/09/2026

A PR #75 entrou na `main` (`ab1b5da`) e a API desse commit foi publicada em
produção. A dashboard e a API são **dois deploys**: merge do front não prova
publicação do back. Nesta entrega, a dashboard nova recebeu 404 da API antiga
até o deploy separado de `fraus-api`. Conferir rotas pelo proxy faz parte do
fechamento de uma alteração de contrato; `/saude` sozinho não basta.

- Análise com gravação alimenta filtros, indicadores e grafo; as rotas avulsas
  seguem sem gravar. IDs `analise:` deduplicam reenvios.
- O NPS é inferido; o cartão respeita ponto nulo abaixo de 30 conversas com
  sinal. AW(3,T) mede incerteza amostral, não erro do modelo.
- Papel global (`dev`/`usuario`) e hierarquia da equipe
  (`proprietario`/`gestor`/`membro`) são contratos diferentes. Convite não
  promove para `dev`; papel ausente não libera controles de gestão.
- `integrantes` e `meu_papel` vêm do servidor. Resposta antiga/incompleta não
  pode quebrar a tela nem ser tratada como permissão administrativa.
- Aceitar convite exige JWT. Login desativado no modo local não habilita o
  aceite pela credencial técnica.

Contratos, evidências e pendências de configuração estão em
[Operação e produção](docs/notas/2026-09-30-operacao-producao.md).

## Comandos

```bash
uv sync --extra dev --extra torch   # `uv sync` puro REMOVE o pytest e o torch (os dois são extras)
uv sync --extra dev --extra onnx    # alternativa sem torch: FRAUS_BACKEND=onnx lê modelos-onnx/
uv run pytest -q
uv run python scripts/api_demo.py      # :8000, dados sintéticos temporários; nunca produção
uv run python -m uvicorn fraus.api.main:app --port 8001 --reload --reload-dir fraus
FRAUS_BACKEND=onnx uv run python -m uvicorn fraus.api.main:app --port 8001 --reload --reload-dir fraus
cd dashboard && npm run dev            # SÓ dentro de dashboard/ — não há package.json na raiz

uv sync --extra dev --extra torch --extra docs  # docs sem remover os extras do desenvolvimento Torch
uv run python scripts/reunir_docs.py   # traz dashboard/DESIGN.md para docs/
uv run mkdocs serve -a localhost:8010  # não disputa :8000 (demo) nem :8001 (API real)
uv run mkdocs build --strict           # build INTERNO (tudo, com codigo-fonte)
uv run mkdocs build --strict --config-file mkdocs-publico.yml   # o que vai pro ar
```

**O repositório é privado e o site é público**, e a fronteira entre os dois é
`mkdocs-publico.yml`: ele exclui `superpowers/`, `notas/`, `handoff.md` e
`hospedagem.md`, e desliga o `show_source` (que embute o **corpo das funções**
no HTML). `not_in_nav` **não** exclui do build — só silencia o aviso. Guardas
em `tests/test_documentacao.py` e no workflow.

O **PDF** não sai no `mkdocs.yml` do dia a dia: ele usa WeasyPrint, que exige
as libs nativas do GTK e não importa no Windows. Ele mora em `mkdocs-pdf.yml`
(`INHERIT` do principal) e roda só no CI Linux — ver `.github/workflows/docs.yml`.

---

## Invariantes — quebrar qualquer uma é bug, não escolha de estilo

1. **Sem LLM em runtime.** Inferência local em CPU. Nenhuma chamada de rede no
   caminho de predição. É requisito do trabalho, não otimização.
2. **Ausência de dado não é insatisfação.** Conversa sem fala do cliente tem
   `score: None` e aparece como "sem sinal" — nunca 0, em lugar nenhum: célula,
   gráfico, ordenação, export, agregado. Procure `?? 0` e `|| 0` antes de commitar.
3. **Score, nota e categoria são derivados no SERVIDOR.** Nunca aceitos do corpo da
   requisição, nunca recalculados no cliente. O modelo de entrada de importação
   aceita só `caminho`. Duplicar a regra no TypeScript já causou divergência de
   arredondamento nas fronteiras 6/7 e 8/9 — não repita.
4. **Faixas de NPS: 0–6 detrator, 7–8 neutro, 9–10 promotor** — padrão de fábrica,
   em `FAIXAS_NPS`. Configuráveis por `PUT /configuracoes`, e só se cobrirem 0..10
   de forma contígua. A faixa vigente é passada **por parâmetro** para
   `categoria_nps`/`calcular_nps` — nunca estado global mutável, nunca digitada
   de novo em outro lugar. A categoria é **derivada na leitura**; o `score`
   gravado nunca é recalculado.
5. **Latência nunca é persistida.** Sempre derivada dos timestamps na leitura.
6. **Timestamps timezone-aware.** `datetime` naive é erro de validação.
7. **Modelo ausente é falha alta e explícita.** Servir predição sem modelo
   carregado é pior que estar fora do ar. Sem fallback, sem motor dublê silencioso.
8. **A ordem das classes é 0 insatisfeito, 1 neutro, 2 satisfeito** — no notebook,
   no sinal de texto, no fusor e nos indicadores. Inverter não gera erro: faz o
   sistema pontuar ao contrário em silêncio.
9. **As 39 chaves de feature** produzidas pelas SETE famílias do vetor batem
   exatamente com `NOMES_FEATURES`. `vetorizar` levanta `KeyError` em falta —
   nunca zero silencioso. Emoção, léxico, ironia e estilo entraram no vetor em
   21/08/2026; a família `incongruencia_*` entrou em 03/09/2026; a ironia SAIU
   de novo em 04/09/2026 (`ironia_prob_media`/`ironia_prob_max` medem sentimento
   positivo, não ironia, no corpus de treino — ver `docs/treinamento.md`), e
   `incongruencia_situacao_negativa` entrou no mesmo dia — daí 40 − 2 + 1 = 39.
   O número aqui é o contrato: se ele divergir de `len(NOMES_FEATURES)`, é este
   arquivo que está errado, e ele governa toda sessão de agente.
   `montar_features` exige DOIS classificadores (texto, emoção); o `Motor`
   continua exigindo os TRÊS (a ironia entra na leitura por mensagem, não no
   vetor), e a API não sobe sem os três modelos treinados.
10. **Corpus de treino não pode entregar o rótulo.** Faixa de latência disjunta
    por classe fez o primeiro fusor marcar 99,3% lendo só o relógio, com o
    BERTimbau apagado. Distribuição por rótulo se sobrepõe; feature constante no
    treino nasce com peso zero. Acurácia alta demais é sintoma, não vitória —
    ver `docs/treinamento.md`. Desde 15/09/2026 as quatro features de espera
    entram no vetor em `log1p` (`FEATURES_EM_LOG`, dentro de `vetorizar`) e o
    artefato carrega a escala: `Fusor.carregar` recusa `fusor.joblib` treinado
    em segundos crus, que teria as mesmas 39 features e daria nota errada.

## Convenções

- Python 3.11, gerenciado por `uv`. TypeScript no front.
- **Identificadores e docstrings em português, sem acento nos nomes de símbolo**
  (`latencia_mediana_s`, `mensagens_cliente`). Texto de interface leva acento normal.
- Commits em português, sem acento, no estilo `tipo(escopo): resumo`.
- TDD: teste que falha primeiro, implementação mínima, teste verde, commit.
- Nada de dependência nova sem motivo declarado. Sem base vetorial — a tarefa é
  classificação, e para classificação o fine-tuning vence RAG.

## Honestidade metodológica — vale para código e para texto de tela

- O **NPS é inferido do texto**, não perguntado ao cliente. Toda exibição carrega a
  etiqueta de estimativa. Apresentar como NPS declarado seria falso.
- O **sinal de tempo é treinado em dados sintéticos** calibrados por literatura,
  porque nenhum corpus público de review em português tem timestamps de diálogo.
  Isso é limitação declarada, não segredo.
- Estado vazio **nomeia o que falta**. Nunca preencha com número simulado.
- **A família `emocao_*` faz do Fraus um sistema de reconhecimento de emoção**
  pela letra do EU AI Act — com obrigação de informar quem está exposto
  (Art. 50(3), em vigor desde 02/08/2026) e uma fronteira que o produto não
  cruza: **o Fraus não pontua atendentes**, porque reconhecimento de emoção no
  local de trabalho é proibido desde fev/2025. "Score de performance por
  atendente" é violação, não feature. Escopo, base legal e o que já está de pé
  em [docs/conformidade.md](docs/conformidade.md).

## Documentos

- `docs/superpowers/specs/2026-08-13-dolos-design.md` — spec, decisões e ~35 referências
- `docs/superpowers/plans/2026-08-13-dolos-implementacao.md` — plano de implementação
- `docs/treinamento.md` — os dois notebooks e os artefatos
- `dashboard/DESIGN.md` — sistema de design da interface
- `docs/notas/2026-09-30-operacao-producao.md` — análise persistida, Operação, convites e evidências da publicação
- `docs/deploy-vercel.md` — procedimento interno; dashboard e API publicam separadamente
- `docs/conformidade.md` — EU AI Act: o que obriga e o que **proíbe** (não pontuar atendente)
- `mkdocs.yml` — site interno; `mkdocs-publico.yml` define o recorte publicado
