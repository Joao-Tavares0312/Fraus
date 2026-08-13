# Fraus — instruções do projeto

Ferramenta de IA que analisa atendimentos de chatbot e mede satisfação do cliente
**sem LLM em runtime**. Trabalho acadêmico, será apresentado numa banca.

---

## Arquitetura em uma tela

```
CSV / Discord / WhatsApp
        ↓  adapter de ingestão (fraus/ingest/)
   Conversa  ← modelo canônico único (fraus/modelos.py)
        ↓
  ┌─────────┴─────────┬──────────────┐
  │ texto             │ emoji        │ tempo
  │ BERTimbau         │ lexicon      │ latência
  │ POR MENSAGEM      │ + posição    │ escalação/abandono
  └─────────┬─────────┴──────────────┘
            ↓  16 features
      Fusor (LogisticRegression + StandardScaler)
            ↓  score 0–100
   nota 0–10 → categoria NPS → indicadores agregados
            ↓
      FastAPI  →  dashboard Next.js
```

## Mapa de arquivos

| Caminho | Responsabilidade |
|---|---|
| `fraus/modelos.py` | `Conversa` / `Mensagem` — modelo canônico |
| `fraus/ingest/csv_driver.py` | CSV → conversas, isolando linha malformada |
| `fraus/ingest/simulador.py` | conversas sintéticas determinísticas (treino do sinal de tempo) |
| `fraus/sinais/texto.py` | BERTimbau, probabilidade **por mensagem** |
| `fraus/sinais/emoji.py` | lexicon + posição relativa |
| `fraus/sinais/tempo.py` | latência, escalação, abandono |
| `fraus/fusor.py` | `NOMES_FEATURES` (16) e o `Fusor` |
| `fraus/indicadores.py` | NPS, CSAT, containment, nota, categoria |
| `fraus/configuracao.py` | configuração vigente: padrão de fábrica no código, delta no banco |
| `fraus/db.py` | SQLite, sem ORM |
| `fraus/api/main.py` | FastAPI: `criar_app` (fábrica) e `app` (lazy, PEP 562) |
| `dashboard/` | Next.js — ver `dashboard/DESIGN.md` |
| `notebooks/` | treino no Colab (BERTimbau, depois fusor) |
| `scripts/api_demo.py` | servidor de demonstração, motor dublê — **nunca em produção** |

## Comandos

```bash
uv sync --extra dev              # `uv sync` puro REMOVE o pytest (grupo dev é opt-in)
uv run pytest -q
uv run python scripts/api_demo.py      # API de demonstração, sem modelo
uv run uvicorn fraus.api.main:app      # API real — exige modelos/ treinado
cd dashboard && npm run dev            # SÓ dentro de dashboard/ — não há package.json na raiz
```

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
9. **As 16 chaves de feature** produzidas pelos três sinais batem exatamente com
   `NOMES_FEATURES`. `vetorizar` levanta `KeyError` em falta — nunca zero silencioso.

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

## Documentos

- `docs/superpowers/specs/2026-08-13-dolos-design.md` — spec, decisões e ~35 referências
- `docs/superpowers/plans/2026-08-13-dolos-implementacao.md` — plano de implementação
- `docs/treinamento.md` — os dois notebooks e os artefatos
- `dashboard/DESIGN.md` — sistema de design da interface
