# CLAUDE.md

Orientações para o Claude Code neste repositório.

## Contexto

Trabalho prático 1 de ISIA (FCUP, 2026/27), tópico O: um sistema multiagente em SPADE para resposta médica de emergência comunitária descentralizada (CEMR). O grupo tem dois estudantes.

- Código em `src/cemr/`, testes em `tests/`, cenários em `scenarios/`, experiências em `experiments/`.
- Desenho em `docs/` (análise Gaia, desenho arquitetural, desenho detalhado, protocolos).
- Plano atual em `PLANO-IMPLEMENTACAO.md`. Instalação e comandos no `README.md`.

## Princípio geral

O trabalho deve ser feito como se fosse feito por estudantes universitários: rigoroso e bem justificado, mas com uma dimensão e uma complexidade proporcionais a um trabalho de uma unidade curricular. Tudo o que for produzido tem de poder ser explicado e defendido pelo grupo na apresentação.

## Língua

- Português europeu (pt-PT) em todo o texto escrito: relatório, slides, documentação, comentários novos, mensagens de commit e respostas. Usar a grafia do Acordo Ortográfico (ação, objetivo, ficheiro, utilizador, equipa).
- Termos técnicos em inglês quando são os usados na área e a tradução soa forçada: agent, behaviour, Contract Net, failover, seed, timeout, baseline, dashboard, trade-off. Na primeira ocorrência num documento, um termo menos comum pode levar uma explicação curta.
- Não traduzir nomes de protocolos, métricas, classes ou ficheiros (P01-P28, M1-M13, `TrustTable`).
- Identificadores no código (variáveis, funções, classes, ficheiros) ficam em inglês, como no código existente.
- Nos ficheiros que já estão escritos em inglês (a maior parte do código e o `README.md`), manter a língua do ficheiro para não misturar. Não traduzir ficheiros inteiros sem pedido.

## Estilo de escrita

- Sem emojis, em lado nenhum: código, documentação, commits e respostas.
- Sem texto com ar de gerado por IA. Em concreto, evitar:
  - frases de enchimento e transições vazias ("É importante notar que", "Em suma", "Vale a pena referir", "Neste contexto");
  - adjetivos vagos ou promocionais ("robusto", "abrangente", "inovador", "poderoso", "de forma eficiente", "solução completa");
  - conclusões que repetem o que acabou de ser dito;
  - excesso de negrito, listas e títulos; quando a ideia é um raciocínio, escrever em texto corrido;
  - travessões em série e frases de efeito ("não é só X, é Y").
- Tom de relatório académico: direto, na primeira pessoa do plural ("implementámos", "observamos") ou impessoal. Frases curtas. Explicar o porquê das decisões e não só o quê.
- Assumir limitações e resultados negativos em vez de os esconder.

## Código

Seguir boas práticas, ao nível do que já existe no repositório:

- PEP 8, type hints nas assinaturas, docstrings curtas onde a lógica não é óbvia (por exemplo, a fórmula usada e a referência, como em `behaviours/reputation.py`).
- Nomes descritivos e funções pequenas com uma só responsabilidade.
- Comentários explicam o porquê, não repetem o que o código já diz.
- Parâmetros numéricos vão para `scenarios/defaults.toml`, documentados, e não ficam como constantes soltas no código.
- A lógica de decisão pura fica em `behaviours/`, separada dos agentes SPADE, para poder ser testada sem XMPP.
- Tratar erros onde eles podem de facto acontecer. Não envolver tudo em `try/except` genéricos.
- Sem código morto, código comentado ou `print` de debug esquecidos.

## Nível de complexidade

- Preferir a solução mais simples que resolve o problema e cumpre o enunciado.
- Usar a biblioteca standard e as dependências que já estão no `pyproject.toml`. Não acrescentar dependências sem uma razão concreta.
- Evitar abstrações prematuras: hierarquias de classes, factories, registries, metaclasses, sistemas de plugins ou configuração genérica para casos que não existem.
- Não otimizar sem ter medido primeiro.
- Usar modelos e algoritmos conhecidos da UC ou da literatura (Gaia, Contract Net, reputação Beta) em vez de soluções inventadas, sempre com referência.
- Se uma alteração parecer exigir muita complexidade, parar e apresentar as alternativas antes de implementar.

## Rigor

- Não inventar resultados, referências nem citações. Cada número apresentado vem de `results/` ou de um run identificado; cada afirmação sobre o sistema aponta para o código ou para o desenho em `docs/`.
- Reprodutibilidade: tudo o que é aleatório depende da seed do run. Os resultados finais vêm de uma única matriz corrida sobre código congelado, com o commit registado.
- Comparações com intervalos de confiança a 95 % e, quando possível, emparelhadas por seed. Não tirar conclusões de um único run.
- Cada alteração de lógica é acompanhada de testes em `tests/`. Correr `pytest -m "not slow"` antes de dar uma tarefa por concluída e o `pytest` completo quando se mexe em agentes ou protocolos.
- Depois de mexer em coordenação, privacidade ou failover, verificar as regras organizacionais com `python -m cemr.metrics.check runs/<run> -v`.
- Manter o código e a documentação coerentes: se uma decisão de desenho muda, atualizar o documento correspondente em `docs/`.
- Se algo não foi testado ou verificado, dizê-lo explicitamente.

## Git

- Commits pequenos, com mensagem em português no imperativo ("Corrige a deduplicação P26 entre células").
- Alterações maiores num branch próprio, integradas por pull request.
- Não fazer commit de `runs/`, `.venv/` nem de ficheiros gerados fora de `results/`.

## Comandos

```bash
source .venv/bin/activate
pytest -m "not slow"                          # testes unitários (< 1 s)
pytest                                        # inclui dois runs SPADE end-to-end (~1,5 min)
python -m cemr.run --scenario c1 --seed 1     # um run do cenário C1
python -m cemr.metrics.check runs/<run> -v    # verificação das regras organizacionais
python experiments/run_matrix.py --matrix main --seeds 1-5 --workers 4
python experiments/analyse.py                 # gera summary.csv, summary.md e figuras em results/
```
