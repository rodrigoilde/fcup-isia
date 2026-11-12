# CLAUDE.md

Orientações para o Claude Code neste repositório.

## Contexto

Trabalho prático 1 de ISIA (FCUP, 2026/27), tópico O: um sistema multiagente em SPADE para resposta médica de emergência comunitária descentralizada (CEMR). O grupo tem dois estudantes. Entrega e apresentação a 19-20 de novembro de 2026.

- Código em `src/cemr/`, testes em `tests/`, cenários em `scenarios/`, experiências em `experiments/`.
- Desenho em `docs/` (análise Gaia, desenho arquitetural, desenho detalhado, protocolos). Enunciado em `docs/assignment.pdf`.
- Plano atual em `PLAN.md`. Instalação e comandos no `README.md`.

## O que o enunciado pede

- Sistema multiagente em SPADE, com instruções claras para correr as simulações.
- Descrição dos agentes, formatos de mensagem, especificação dos protocolos, modos de falha, métricas de desempenho e justificação das decisões de desenho.
- Avaliação em pelo menos três cenários de teste contrastantes, com resultados, trade-offs e limitações.
- Documentação do código, uma visualização ou demo das interações e das métricas, e slides para a apresentação.
- Testes unitários e scripts que reproduzem as experiências (opcionais no enunciado, mas já fazem parte do projeto).

## Princípio geral

O trabalho deve ser feito como se fosse feito por estudantes universitários: rigoroso e bem justificado, mas com uma dimensão e uma complexidade proporcionais a um trabalho de uma unidade curricular. Tudo o que for produzido tem de poder ser explicado e defendido pelo grupo na apresentação.

No código, isto quer dizer código simples e sintetizado, como o escreveriam dois estudantes do 3.º ano. Qualquer um dos dois tem de conseguir explicar cada ficheiro, incluindo numa eventual prova oral. Entre uma solução elegante e uma óbvia, escolher a óbvia.

## Língua

- Português europeu (pt-PT) em todo o texto escrito: relatório, slides, documentação, comentários, docstrings, mensagens de commit e respostas. Usar a grafia do Acordo Ortográfico (ação, objetivo, ficheiro, utilizador, equipa).
- Termos técnicos em inglês quando são os usados na área e a tradução soa forçada: agent, behaviour, Contract Net, failover, seed, timeout, baseline, dashboard, trade-off. Na primeira ocorrência num documento, um termo menos comum pode levar uma explicação curta.
- Não traduzir nomes de protocolos, métricas, classes ou ficheiros (P01-P28, M1-M13, `TrustTable`).
- Identificadores no código (variáveis, funções, classes, ficheiros) ficam em inglês, como no código existente.
- Comentários e docstrings são sempre em português. Ao editar um ficheiro que ainda os tem em inglês, traduzi-los no ficheiro todo, para não haver mistura dentro do mesmo ficheiro.
- O `README.md` e os documentos em `docs/` mantêm a língua em que estão escritos. Não os traduzir sem pedido.

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

Seguir boas práticas (PEP 8 para o estilo, PEP 257 para as docstrings):

- Type hints nas assinaturas, nomes descritivos e funções pequenas com uma só responsabilidade.
- Comentários explicam o porquê, não repetem o que o código já diz.
- Códigos internos (P01-P28, OS1, D6, M1-M13) aparecem sempre com uma explicação em palavras: `# OS1: só um hub é dono do caso de cada vez`, nunca só `# OS1`. A notação formal do Gaia (expressões de liveness, tabelas de estados) fica em `docs/`; no código basta uma frase e a referência à secção.
- Parâmetros numéricos vão para `scenarios/defaults.toml`, documentados, e não ficam como constantes soltas no código.
- A lógica de decisão pura fica em `behaviours/`, separada dos agentes SPADE, para poder ser testada sem XMPP.
- Tratar erros onde eles podem de facto acontecer. Não envolver tudo em `try/except` genéricos.
- Sem código morto, código comentado ou `print` de debug esquecidos. Os registos passam pelo event log do agente (`self.log(...)`).

### Docstrings

Estilo Google, igual em todo o projeto:

- Primeira linha com um resumo curto. Depois, só se for preciso, uma descrição e as secções `Args:`, `Returns:`, `Raises:` e `Attributes:`. Os nomes das secções ficam em inglês, porque é isso que o pdoc reconhece. Cada entrada tem o formato `nome (tipo): descrição`.
- Docstring em todos os módulos, classes e funções públicas. A do módulo diz o que o módulo faz, que papel Gaia ou protocolo implementa e qual a secção de `docs/` correspondente. Os atributos de uma classe documentam-se na secção `Attributes:` da docstring da classe.
- Numa subclasse ou num método redefinido, se o comportamento não muda, não repetir a docstring; se muda, documentar só a diferença.
- A docstring de cada classe de agente indica o tipo de agente e a arquitetura (ver "Conceitos da UC").
- Fórmulas levam a referência bibliográfica, como em `behaviours/reputation.py`.
- Não descrever o que é óbvio pela leitura do código.

```python
def trust(self, pseudonym: str) -> float:
    """Calcula a confiança numa fonte com o modelo de reputação Beta.

    Usa a média da distribuição Beta, (a + 1) / (a + b + 2), somando às
    contagens próprias as recomendações dos hubs vizinhos (Jøsang e Ismail, 2002).

    Args:
        pseudonym (str): Pseudónimo da fonte.

    Returns:
        float: Confiança entre 0 e 1 (0.5 quando ainda não há observações).
    """
```

## Nível de complexidade

- Preferir a solução mais simples que resolve o problema e cumpre o enunciado.
- Código curto, mas não críptico: evitar compreensões aninhadas, lambdas compridas, o operador `:=`, ternários encadeados e expressões que precisam de ser lidas duas vezes.
- Como referência, funções até 30 linhas e módulos abaixo de 300. Ao mexer num módulo maior (por exemplo `agents/case_fsm.py` ou `protocol/messages.py`), dividi-lo por estado ou por protocolo.
- Estruturas de dados simples: `dict`, `list` e `dataclass` sem truques. `Enum` só para conjuntos fixos de valores usados em vários sítios.
- Usar a biblioteca standard e as dependências que já estão no `pyproject.toml`. Não acrescentar dependências sem uma razão concreta.
- Evitar abstrações prematuras: hierarquias de classes, factories, registries, decorators que registam classes, metaclasses, `__getattr__`, sistemas de plugins ou configuração genérica para casos que não existem. Não abstrair antes de haver pelo menos três usos repetidos.
- Não otimizar sem ter medido primeiro.
- Usar modelos e algoritmos conhecidos da UC ou da literatura (Gaia, Contract Net, reputação Beta) em vez de soluções inventadas, sempre com referência.
- Se uma alteração parecer exigir muita complexidade, parar e apresentar as alternativas antes de implementar.

### Ao simplificar código existente

1. Um módulo de cada vez, sem mudar o comportamento. Correr `pytest -m "not slow"` antes e depois.
2. No fim, correr o `pytest` completo e o verificador de regras num run curto (ver Comandos).
3. Não mudar mensagens, protocolos ou métricas sem atualizar `docs/04-protocols-and-messages.md` e `metrics/check.py`.
4. Os números em `results/` vêm de uma matriz corrida sobre código congelado. Se a simplificação mudar a lógica e não só a forma, avisar: a matriz tem de ser corrida de novo antes de os números entrarem no relatório.
5. Uma refatoração que toque em mais de um ficheiro ou em mais de cerca de 150 linhas começa por um plano curto, apresentado antes de mexer no código.

## SPADE

SPADE 4.1.4, com Python 3.10-3.14. Usar as construções da própria framework antes de criar infraestrutura nova.

- Um agente é uma subclasse de `Agent`, e os behaviours são adicionados em `async def setup()`.
- Escolher o behaviour pelo padrão de execução: `OneShotBehaviour` para uma tarefa única, `CyclicBehaviour` para um ciclo de receção, `PeriodicBehaviour` para tarefas periódicas, `TimeoutBehaviour` para uma tarefa a uma hora marcada, e `FSMBehaviour` com `State` para conversas com vários passos, como o ciclo de vida de um caso.
- Numa `FSMBehaviour`, todos os estados partilham o mesmo template e a mesma fila de mensagens. Cada estado escolhe o seguinte com `set_next_state`, usando o nome com que foi registado e só para transições registadas com `add_transition`; caso contrário a FSM termina com `NotValidState` ou `NotValidTransition`. Um estado que não chama `set_next_state` é final.
- `send` e `receive` são corrotinas e levam sempre `await`. `receive(timeout=...)` devolve `None` quando não chega nada, e esse caso tem de ser tratado.
- `kill()` só marca o behaviour para terminar na iteração seguinte; para sair da iteração atual é preciso `return`.
- Uma exceção em `on_start`, `run` ou `on_end` termina o behaviour sem aviso e fica guardada em `exit_code`. Quando um behaviour pára sem razão aparente, é o primeiro sítio a ver.
- Nunca bloquear o event loop (`time.sleep`, ciclos longos sem `await`). As esperas em tempo simulado fazem-se com `await self.agent.sleep(...)`.
- Cada mensagem leva em metadata os campos FIPA-ACL `performative`, `ontology`, `language` e `protocol`. O `thread` da mensagem faz de conversation-id, e o corpo é JSON.
- Em código novo, encaminhar mensagens com `Template` (por metadata, combináveis com `&`, `|` e `~`). O SPADE entrega uma mensagem a todos os behaviours cujo template coincide, por isso os templates têm de ser disjuntos. É por isso que existe o `Router` em `agents/base.py`; só o substituir por templates se o `pytest` completo continuar a passar.
- Os dados partilhados entre behaviours ficam em atributos do agente (ou em `self.agent.get`/`set`), nunca em variáveis globais.
- O servidor XMPP embutido usa `localhost`, por isso os JID têm a forma `nome@localhost`.

## Conceitos da UC

O código, os comentários e o relatório usam os conceitos dados nas aulas, com os mesmos nomes. Quando uma decisão corresponde a um destes conceitos, dizê-lo no comentário, na docstring ou no relatório.

- Agente (Wooldridge): sistema computacional situado num ambiente, capaz de ação autónoma para cumprir os objetivos que lhe foram delegados. Propriedades: autonomia, reatividade, proatividade e capacidade social.
- Tipos de agente (Russell e Norvig): reflexo simples, reflexo com modelo, baseado em objetivos, baseado em utilidade e com aprendizagem.
- Arquiteturas: reativa (subsunção), deliberativa (BDI: crenças, desejos, intenções) e híbrida em camadas.
- Metodologia Gaia: papéis com responsabilidades de liveness e safety, protocolos, modelo de agentes e modelo de serviços. Uma funcionalidade nova começa pelo papel e pelo protocolo em `docs/`, e só depois passa ao código.
- Comunicação: teoria dos atos de discurso e FIPA-ACL. `inform` e `request` são as performativas base. Usar só performativas FIPA, com o significado da especificação: `inform`, `request`, `agree`, `refuse`, `failure`, `cfp`, `propose`, `accept-proposal`, `reject-proposal`, `query-if`, `query-ref`, `subscribe`, `cancel`.
- Protocolos de interação: preferir os protocolos FIPA (Request, Query, Request-When, Subscribe, Propose, Contract Net, Iterated Contract Net, English Auction, Dutch Auction, Brokering, Recruiting) e dizer qual se segue. O Contract Net segue a sequência `cfp`, depois `propose` ou `refuse`, depois `accept-proposal` ou `reject-proposal`, e por fim `inform` ou `failure`. Um protocolo próprio só quando nenhum destes serve, com justificação em `docs/04-protocols-and-messages.md`.
- Decisão multiagente: para agregar preferências ou alocar recursos, usar mecanismos conhecidos, como votação (pluralidade, Borda, vencedor de Condorcet), leilões (inglês, holandês, first-price sealed-bid, Vickrey) e Contract Net. Discutir as propriedades relevantes: condição de Pareto, vencedor de Condorcet, independência de alternativas irrelevantes e manipulação estratégica (o leilão de Vickrey, de segundo preço, torna a licitação honesta a melhor estratégia).
- Simulação baseada em agentes: manter separados os agentes, o ambiente (`sim/`), o escalonamento no tempo (o relógio simulado) e a recolha de dados (`metrics/`).
- Bibliografia de base, a citar primeiro: Wooldridge, *An Introduction to MultiAgent Systems* (2.ª ed., 2009); Russell e Norvig, *Artificial Intelligence: A Modern Approach* (4.ª ed., 2022); Shoham e Leyton-Brown, *Multiagent Systems* (2008); especificações FIPA dos protocolos usados.

## Rigor

- Não inventar resultados, referências nem citações. Cada número apresentado vem de `results/` ou de um run identificado; cada afirmação sobre o sistema aponta para o código ou para o desenho em `docs/`.
- Reprodutibilidade: tudo o que é aleatório depende da seed do run. Os resultados finais vêm de uma única matriz corrida sobre código congelado, com o commit registado.
- Comparações com intervalos de confiança a 95 % e, quando possível, emparelhadas por seed. Não tirar conclusões de um único run.
- Cada alteração de lógica é acompanhada de testes em `tests/`, simples e com um comportamento por teste. Correr `pytest -m "not slow"` antes de dar uma tarefa por concluída e o `pytest` completo quando se mexe em agentes ou protocolos.
- Depois de mexer em coordenação, privacidade ou failover, verificar as regras organizacionais com `python -m cemr.metrics.check runs/<run> -v`.
- Manter o código e a documentação coerentes: se uma decisão de desenho muda, atualizar o documento correspondente em `docs/`.
- Se algo não foi testado ou verificado, dizê-lo explicitamente.

## Git

- Commits pequenos, com mensagem em português no imperativo ("Corrige a deduplicação P26 entre células").
- Alterações maiores num branch próprio, integradas por pull request.
- Não fazer commit de `runs/`, `.venv/` nem de ficheiros gerados fora de `results/`.

## Comandos

```bash
.venv\Scripts\activate                        # Windows; em macOS/Linux: source .venv/bin/activate
pytest -m "not slow"                          # testes unitários (< 1 s)
pytest                                        # inclui dois runs SPADE end-to-end (~1,5 min)
python -m cemr.run --scenario c1 --seed 1     # um run do cenário C1
python -m cemr.run --scenario c4 --seed 1 --duration 1500 --factor 30   # run curto, para verificações rápidas
python -m cemr.metrics.check runs/<run> -v    # verificação das regras organizacionais
python experiments/run_matrix.py --matrix main --seeds 1-5 --workers 4
python experiments/analyse.py                 # gera summary.csv, summary.md e figuras em results/
pdoc src/cemr -o docs/api                     # documentação HTML a partir das docstrings (pip install pdoc)
```
