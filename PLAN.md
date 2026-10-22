# Plano — ISIA 2026/27 · Assignment 1 · Tópico O (Decentralised Community Emergency Medical Response)

## Contexto

- **O que é:** o Assignment 1 de ISIA vale 70% da nota de trabalhos (35% da nota final) e é feito em grupos de 3.
- **Prazo:** entrega e apresentação na semana 9, **19–20 Nov 2026**. Hoje é 22 Out, o que dá cerca de 4 semanas.
- **O que o enunciado pede:**
  - um SMA em **SPADE**, acompanhado da descrição dos agentes, formatos das mensagens, modos de falha, métricas e justificação das escolhas;
  - **≥3 cenários contrastantes**;
  - código com instruções, documentação, relatório de desempenho, visualização/demo e slides;
  - testes, que são opcionais.
- **O que já está feito:** a fase de **análise Gaia** completa, em `isia/Análise Gaia — Tópico O (Resposta Médica de Emergência).pdf`. Inclui:
  - 14 RF, 9 RNF e 8 pressupostos;
  - 4 sub-organizações (SO-DV, SO-DR, SO-AT, SO-CP);
  - 18 recursos de ambiente, 12 papéis (R1–R12) e 24 protocolos (P01–P24);
  - as regras OL1–OL9 e OS1–OS13;
  - 13 métricas, 5 cenários, 2 baselines, parâmetros iniciais (§8.3), 15 modos de falha (§8.4) e 8 decisões em aberto (D1–D8).
- **O que falta:** o **design arquitetural**, o **design detalhado** (fases Gaia), a implementação SPADE, a avaliação e os entregáveis.
- **Onde fica tudo:** no repo `fcup-isia` (github.com/rodrigoilde/fcup-isia), que por agora só tem o enunciado.
- **Escolhas já feitas:**
  - topologia em hierarquia leve por célula;
  - só behaviours SPADE (sem BDI);
  - dashboard web ao vivo com vídeo de backup;
  - entregáveis em **inglês**, com identificadores em inglês como já está na análise.

---

## 1. Design arquitetural — fechar D1–D8

| ID | Decisão | Escolha | Justificação (critério da §9.2) |
|---|---|---|---|
| D1 | Topologia | **Hierarquia leve por célula.** Cada armário de DAE é o *hub* da sua célula (partição de Voronoi da grelha pelos DAE: 10 DAE = 10 células). Os hubs vizinhos são pares entre si. | Garante OS1/OS7/OS13 de forma trivial. Custo de mensagens (M8) limitado. Continua sem despachante central, porque cada hub só vê a sua célula. |
| D2 | Quem é IncidentVerifier e IncidentCoordinator | O hub da célula onde surge o 1.º alerta. A passagem P06 é interna ao agente e fica registada no auditLog. | OS7: o hub nunca emite alertas. OS1: há um dono estável por caso. |
| D3 | Descoberta de socorristas | Voluntários e testemunhas fazem **subscribe** ao hub da célula atual (FIPA-Subscribe), enviando pseudónimo, qualificação e célula, **nunca coordenadas**. Voltam a registar-se quando mudam de célula. A CFP vai para a célula do caso e o anel vizinho; sem propostas, alarga ao 2.º anel. | Privacidade (M11) com rapidez aceitável (M3). Evita a presença XMPP, que a nota §9.4 diz ser instável no pyjabber. |
| D4 | Alocação | **Contract Net FIPA** com redundância controlada (P1: 2 RCP + 1 DAE, `N_max=4`). Ranking por ETA, qualificação e confiança. Com contenção, os casos são servidos por prioridade. A EMS pode ser preemptada P3→P1 (OS9). | M3, M9, M10. Comparado com a B1 ("primeiro a aceitar"). |
| D5 | Fusão e limiares | **Log-odds bayesiano:** cada evidência soma `trust·log LR(tipo)`. Usa `τ_declare(p)` e `W_max(p)` da §8.3 e a regra de independência OS4. As políticas AlertFirst e ConfirmFirst são parâmetro. | Trade-off entre M1 e M2, testado em C2. |
| D6 | Confiança | **Beta reputation** (α, β) por pseudónimo em cada hub, com decaimento para o prior. **Gossip** P23 entre hubs vizinhos, descontado pela confiança no par. Pseudónimo novo começa no prior. | M2 em C2/C5, OS13. |
| D7 | Privacidade | Pseudónimos por caso; os alertas só levam a célula. A localização precisa só se obtém via **P24** ao PrivacyGuardian do titular, e o coordenador só a passa dentro do `AwardTask`. Dados clínicos só para a EMS. Purga após `T_ret`. | M11 vs M8. A variante "divulgação direta aos adjudicados" fica opcional. |
| D8 | Recuperação | O hub replica o estado compacto do caso para o **sucessor determinístico** (hub vizinho de menor id) a cada mudança de estado, com heartbeat e lease. Quando a lease expira, o sucessor assume o caso. Fusão de duplicados na fronteira: o hub emite `CandidateOpen` aos vizinhos e, havendo sobreposição, fica com o caso quem o abriu primeiro (empate: hub de menor id). | Preserva OS1, M12 (F6, F14). |

Papéis novos ditados pela estrutura (§9.2): **nenhum obrigatório**. O `CellCoordinator` é o próprio hub, e o `CaseRegistry` é substituído pelo `CandidateOpen` entre vizinhos.

## 2. Design detalhado

### 2.1 Modelo de agentes (Gaia)

| Agente SPADE | Papéis Gaia | N (C1, §8.3) |
|---|---|---|
| `CitizenDeviceAgent` | SensorMonitor + PrivacyGuardian (do portador) | 40 |
| `BystanderAgent` | WitnessReporter + OnSceneHelper (modelo humano) + BystanderGuide (app local) + PrivacyGuardian (da própria localização) | 15 |
| `VolunteerAgent` | VolunteerResponder + AEDRunner (consoante o tipo de tarefa) | 30 |
| `AEDHubAgent` | AEDCustodian + IncidentVerifier + IncidentCoordinator + ReputationManager | 10 |
| `EMSAgent` | EMSUnit | 4 |
| Infraestrutura, fora do Gaia | `World` (ambiente), `SimClock`, `NetworkModel`, `FaultInjector`, `EventLog`, dashboard | — |

- **P16/P17 dentro do `BystanderAgent`:** ficam numa fila asyncio local, fora do XMPP, para a orientação funcionar sem rede (F13). Continuam registados como eventos de protocolo.
- **Um caso, um FSM no hub:** cada caso é um **FSMBehaviour dinâmico** com `Template(thread=case_id)`, o que permite vários incidentes em simultâneo (RNF3).

### 2.2 Modelo de serviços e mapeamento para SPADE (§9.4)

- **Vivacidade para behaviours:**
  - `(x)^ω` → `CyclicBehaviour` dispatcher;
  - `_SelfTest`, `_DecayTrust`, `ShareReputation` e heartbeat → `PeriodicBehaviour`;
  - janelas e prazos → `receive(timeout)` em tempo simulado;
  - Verify, Contract Net e Guidance → `FSMBehaviour`.
- **Cuidado com o tempo:** `PeriodicBehaviour` e `TimeoutBehaviour` usam relógio real. Por isso todos os períodos e prazos passam por `SimClock.to_real()`.
- **Envelope das mensagens:**
  - metadata: `performative` (FIPA), `protocol` (`"P08-CallForResponders"`), `ontology="cemr-v1"`, `language="json"`;
  - `thread` = id do caso ou candidato.
- **Corpo das mensagens:** JSON gerado a partir de `dataclasses`, uma por protocolo, com `seq` para idempotência (F5).
- **Envio:** todas as mensagens saem por `send_with_faults()` na classe base, que injeta atraso e perda por célula (A3) e regista bytes (M8).

### 2.3 Ambiente de simulação (fora do Gaia, §9.3)

- **`World`:**
  - grelha 3×3 km com distância Manhattan e velocidades por modo (pé, corrida, carro, ambulância);
  - células de Voronoi;
  - recursos `roadNetwork`, `aedRegistry` (público), `patientCondition` e `groundTruth`;
  - acesso por métodos restritos que espelham a matriz ambiente–papéis (§5.4).
- **Incidentes:** Poisson por célula e hora, com mistura P1/P2/P3 e fração de ritmos desfibrilháveis. Os sensores têm TPR/FPR, deriva e bateria.
- **Doente:** proxy de Larsen (M6) e ROSC com probabilidade `p` após choque.
- **Reprodutibilidade:** relógio acelerado (fator calibrado no spike, alvo 10–20×) e **seed fixa** (RNF9).

## 3. Estrutura do repositório `fcup-isia`

```
fcup-isia/
├── README.md                  # setup (venv Python 3.11, spade==4.1.4) e como correr
├── PLAN.md                    # este plano
├── requirements.txt           # spade==4.1.4, numpy, pandas, matplotlib, pytest
├── docs/                      # EN
│   ├── assignment.pdf         # enunciado (mover o PDF atual)
│   ├── 01-gaia-analysis.pdf   # cópia da análise + 01-gaia-analysis-summary.md (EN)
│   ├── 02-architectural-design.md   # D1–D8 + regras organizacionais
│   ├── 03-detailed-design.md        # modelo de agentes + serviços
│   └── 04-protocols-and-messages.md # P01–P24: diagramas de sequência (mermaid) + schemas
├── src/cemr/
│   ├── run.py                 # python -m cemr.run --scenario c1 --seed 1 [--policy ours|naive]
│   ├── sim/        clock.py world.py patient.py incidents.py network.py faults.py
│   ├── protocol/   messages.py (dataclasses P01–P24) templates.py
│   ├── agents/     base.py citizen_device.py bystander.py volunteer.py aed_hub.py ems.py
│   ├── behaviours/ verification.py contract_net.py guidance.py reputation.py privacy.py recovery.py
│   ├── baselines/  oracle_b0.py  (B1 = policy "naive" nos hubs)
│   ├── metrics/    eventlog.py compute.py (M1–M13) check.py (invariantes OL/OS)
│   └── viz/        server.py (aiohttp + WebSocket) static/
├── scenarios/      c1_urban.toml c2_noise.toml c3_surge.toml c4_periphery.toml c5_adversarial.toml
├── experiments/    run_matrix.py analyse.py → results/ (CSV + figuras)
├── tests/
├── report/         performance report (EN)
└── slides/
```

## 4. Avaliação

- **Cenários:** C1 Base urbana, C2 Ruído e falsos alarmes, C3 Pico com contenção, C4 Periferia degradada, mais C5 Adversarial se houver tempo. Os parâmetros saem da §8.2/8.3, em ficheiros TOML.
- **Comparações:**
  - **B1** (difusão ingénua, que é a política `naive` nos hubs) em todos os cenários;
  - **B0** (oráculo centralizado, calculado offline sobre o mesmo traço de incidentes e posições) para M9.
- **Variantes obrigatórias:**
  - AlertFirst vs ConfirmFirst (C2);
  - k = 1/2/3 (C3);
  - reputação on/off (C2, C5).
- **Variantes opcionais:** τ adaptativo; divulgação direta vs via coordenador.
- **Execução:** 5 seeds por configuração e 60 min simulados por run. São cerca de 70 runs, que correm em paralelo (prefixo de JID por run) e durante a noite.
- **Saídas:**
  - `events.jsonl` por run, que também serve de auditLog (OS10);
  - `compute.py` calcula M1–M13 com média e IC95%;
  - `check.py` valida OS1–OS3, OS5, OS6, OS9, OL1, OL2 e OL9 em todos os runs.
- **Relatório:** resultados por cenário, trade-offs (M1↔M2, M11↔M8, redundância↔M10) e limitações (proxy não clínico, grelha sintética, XMPP local).

## 5. Visualização / demo

- **Página `viz/`:**
  - mapa com as células de Voronoi, o estado de cada hub e DAE, voluntários, ambulâncias e incidentes;
  - setas de mensagens coloridas por sub-organização;
  - mosaicos de métricas (M1, M3–M5, M7, casos ativos);
  - linha temporal de protocolos por caso.
- **Modos:** **ao vivo** (WebSocket alimentado pelo EventLog) e **replay** a partir de `events.jsonl`. O replay serve para gravar o vídeo e de fallback na apresentação.

## 6. Cronograma (4 sprints) e divisão sugerida (3 pessoas)

| Sprint | Datas | Objetivos | Saída verificável |
|---|---|---|---|
| 0 | 22–25 Out | Venv **Python 3.11** (o sistema tem 3.9.6, incompatível) com `spade==4.1.4`; esqueleto do repo; **spike de escala** (~100 agentes no servidor embutido, medir latência e escolher o fator de aceleração; fallback Prosody via brew); `02-architectural-design.md` | Spike corre com 100 agentes; fator escolhido |
| 1 | 26 Out–1 Nov | `03`/`04` (agentes, serviços, schemas); núcleo de simulação (clock, world, patient, incidents, network, eventlog); **caminho feliz C1**: P01, P03, P04, P06, P08–P14, P19, P20 | 1 incidente P1 ponta a ponta: declarado → ambulância → voluntário e DAE no local → CloseCase |
| 2 | 2–8 Nov | Orientação P05, P16, P17 (+P15, P18); reputação P21–P23; privacidade P24 + purga; falhas F5–F8, F11, F14 e failover D8; política B1; oráculo B0; `check.py`; dashboard v1 | `check.py` passa; dashboard mostra C1 ao vivo |
| 3 | 9–14 Nov | Cenários C1–C4 (C5 se der); `run_matrix.py`; runs durante a noite; `analyse.py` com tabelas e figuras; testes pytest | `results/` com ≥4 cenários × (ours, B1) × 5 seeds |
| 4 | 15–18 Nov | Relatório (EN), slides, vídeo demo, README final, ensaio | Entregáveis completos; buffer de 1 dia |

**Divisão por sub-organização**, para minimizar dependências:

| Pessoa | Responsabilidades |
|---|---|
| **A** | SO-DV + SO-CP: `citizen_device`, deteção na `bystander`, `verification`, `reputation`, `privacy`; cenários C2/C5 |
| **B** | SO-DR: `aed_hub` (coordenação), `contract_net`, `volunteer`, `ems`, `recovery`; cenários C3/C4 |
| **C** | Infraestrutura + SO-AT: `sim/*`, `eventlog`, `metrics`, baselines, `guidance`, `viz`, `experiments` |

O relatório e os slides são partilhados, e cada pessoa escreve a parte que implementou.

**Prioridades, se faltar tempo:**
- **Obrigatório:** os protocolos núcleo, C1–C4, B0/B1, M1–M12, o dashboard, o relatório e os slides.
- **Opcional:** P15, P18, P23, C5, M13, τ adaptativo e a interface web própria do SPADE.

## 7. Riscos principais

- **Instabilidade do pyjabber com muitos agentes.** Mitigação: o spike no sprint 0; subscribe explícito em vez de presença XMPP; Prosody como plano B; reduzir `CitizenDeviceAgent` se for preciso.
- **Tempo real vs simulado.** Mitigação: um único `SimClock` e o fator calibrado. A latência XMPP é medida à parte (§9.4).
- **Duração das experiências.** Mitigação: correr runs em paralelo com prefixos de JID e começar as runs durante a noite cedo, no sprint 3.
- **Âmbito de 24 protocolos.** Mitigação: implementar primeiro os 21 núcleo; as extensões ficam para o fim.

## 8. Verificação

1. **Testes unitários (`pytest tests/`):**
   - fusão (τ, W_max, regra OS4);
   - Beta (limites [0,1], prior para pseudónimo novo, decaimento);
   - ranking do Contract Net e `N_max`;
   - exclusividade da reserva de DAE (OS3);
   - política de divulgação (OS5);
   - modelo de Larsen.
2. **Smoke:** `python -m cemr.run --scenario c1 --seed 1 --duration 600` produz um caso P1 com a sequência OL1 completa no `events.jsonl`.
3. **Invariantes:** `python -m cemr.metrics.check runs/<id>` não dá nenhuma violação de OS/OL em todos os runs da matriz.
4. **Reprodutibilidade:** a mesma seed dá o mesmo traço de incidentes e o mesmo `groundTruth` (hash igual).
5. **Demo:** abrir `http://localhost:8080` durante um run C1 e confirmar que agentes, mensagens e métricas atualizam; o replay de `events.jsonl` funciona.
6. **Final:** `experiments/run_matrix.py` seguido de `analyse.py` gera as tabelas e figuras do relatório, com ≥3 cenários e comparação com B0/B1.

## Estado

### Sprint 0 — concluído (22 Out)

- **Ambiente:** venv Python 3.11 + `spade==4.1.4`. Foi preciso acrescentar `greenlet`, que o pyjabber usa e o `pip install spade` não instala.
- **Esqueleto:** `pyproject.toml` (instalável com `pip install -e .[dev]`), pacote `src/cemr/`, smoke test com pytest.
- **Spike de escala:** resultados em `spikes/README.md`.
  - 100 e 200 agentes funcionam sem perdas.
  - O fator de aceleração escolhido é **10×**.
  - Mensagens entre agentes do mesmo processo **não passam por XMPP** (o `Container` do SPADE entrega-as em memória). Por isso o `NetworkModel` é a única fonte de latência e perda.
  - O `spade run` tem de levar `--host localhost`.
  - Os agentes arrancam em **lotes com retry**, porque o pyjabber deixa cair ligações em rajadas de login.
- **Design arquitetural:** `docs/02-architectural-design.md`.
  - D1–D8 fechadas.
  - Novos protocolos ditados pela estrutura: **P25** `RegisterInCell`, **P26** `CandidateOpen`, **P27** `ReplicateCase`, **P28** `TakeOverCase`.
  - Os valores enumerados em português passam para inglês no código.

### Sprint 1 — concluído (22 Out, adiantado)

- **Núcleo de simulação** (`src/cemr/sim/`):
  - `SimClock`;
  - `CityGrid`, com células de Voronoi, vizinhos e anéis;
  - `World`, que faz cumprir a matriz ambiente–papéis;
  - `NetworkModel`, com latência log-normal, perda, zonas sem rede e **FIFO por ligação**;
  - layout e traço gerados a partir da seed (o hash do traço é reprodutível);
  - doente com o proxy de Larsen.
- **Protocolo** (`src/cemr/protocol/`):
  - payloads dos 28 protocolos, 63 mensagens com descrição por campo;
  - as tabelas do `04` são geradas a partir delas.
- **Agentes** (`src/cemr/agents/`):
  - `AEDHubAgent`, com um `CaseFSM` por caso: VERIFY → DISPATCH → TRACK → CLOSE/DISCARD;
  - `VolunteerAgent`, com o FSM `Mission`;
  - `EMSAgent`, com o FSM `EMSMission`;
  - `CitizenDeviceAgent`, com as políticas AlertFirst, ConfirmFirst e adaptativa;
  - `BystanderAgent`.
- **Router único por agente:** o SPADE entrega uma mensagem a *todos* os behaviours cujo template coincide.
- **Protocolos implementados:** P01–P04, P06, P08–P14, P19, P20, P24, P25.
- **Lógica pura testada** (`tests/test_logic.py`, 26 testes):
  - fusão e OS4 (D5);
  - Contract Net (D4);
  - divulgação (D7/OS5);
  - custódia do DAE (OS3);
  - Beta (D6);
  - Larsen;
  - FIFO;
  - reprodutibilidade.
- **Teste ponta a ponta** (`tests/test_end_to_end.py`): verifica a sequência OL1, OL2, OL7 e OS5 no caso P1 com guião (S1).
- **Documentos:** `docs/03-detailed-design.md` e `docs/04-protocols-and-messages.md`.
- **Parâmetros alterados face à análise:**
  - `W_max` P1/P2 passa de 30/60 s para **45/75 s**: o prompt ao portador dura 30 s, e com 30 s o 3.º ramo de OS4 nunca fechava;
  - prior de **0,15** com LR calibrados (tabela no `03` §4.1).

### Primeiros resultados C1 (2 seeds em paralelo, servidor partilhado, 10×)

| | seed 1 | seed 2 |
|---|---|---|
| Validade | 360 s reais, paragens ≤ 10 ms | 360 s reais, paragens ≤ 10 ms |
| P1 | 3 (1 indetetável) | 2 |
| Recall (incidentes detetáveis) | 100 % | 100 % |
| Precisão | 100 % | 100 % |
| M1 (mediana) | 19 s | 39 s |
| M3 RCP | 2,1 min | 4,5 min |
| M5 EMS | 5,7 min | 8,7 min |
| DAE antes da EMS | 50 % | 100 % |

**Lições:**
- **Calibração da EMS:** com 60 s de despacho e 36 km/h a EMS chegava em ~2,5 min, o que é irrealista. Passou para 240 s e 30 km/h. **A confirmar com dados do INEM.**
- **Fecho da tampa:** suspende o processo e estraga o run (aconteceu num run: parou em t = 1594 s). O `run.py` deteta-o agora e marca o run como inválido (código de saída 3). As experiências correm na corrente e com `caffeinate -i`.
- **Métricas:** M3–M7 são calculadas sobre incidentes detetáveis. O caminho 112 (A7) fica para o sprint 3, para comparar com as linhas de base sobre todos os incidentes.

### Sprint 2 — concluído (22 Out, adiantado)

- **Protocolos:** os 28 estão implementados:
  - orientação (P05, P15–P18) com modelo humano de cansaço e desistência;
  - retratação (P07);
  - realocação (OL6) e libertação de excedentes (OL8);
  - reputação (P21–P23) com gossip e decaimento;
  - duplicados entre células (P26);
  - failover (P27/P28);
  - retries para perdas (F5).
- **Cenários C2–C4**, com variantes via `--set`:
  - C2 traz sensores com deriva e testemunhas que leem mal a cena;
  - C3 traz um pico de incidentes num evento;
  - C4 traz DAE fechados, ambulâncias longe, zonas sem rede e o crash de um hub.
- **Linhas de base:** B1 (`policy.allocation=naive`) e o oráculo B0 (M9).
- **Métricas M1–M13**, o verificador de regras `metrics/check.py` e a validade de cada run.
- **Experiências:** `experiments/run_matrix.py`, que corre em paralelo e retoma se for interrompido, e `experiments/analyse.py`, que produz tabelas com IC95 % e figuras.
- **Dashboard:** ao vivo (`--viz`) e em replay (`python -m cemr.viz.server`).
- **Testes:** 36 unitários e 2 ponta a ponta (C1 e failover em C4), todos a passar. Os documentos 02, 03, 04 e o README estão atualizados.

**Bugs encontrados e corrigidos neste sprint, a mencionar no relatório:**
- **Prioridade.** Uma testemunha com triagem errada (o erro de observação de 10 %) rebaixava para P3 um P1 detetado por sensor cardíaco, e o caso ficava sem despacho. Agora a prioridade é a mais grave das fontes ativas, e uma triagem incoerente é ignorada.
- **Crash de hub.** O `kill()` do SPADE só atua entre iterações, por isso um hub "crashado" continuava a agir: dois donos do mesmo caso, violação de OS1. Agora `next_incoming` deteta a paragem e um agente parado não envia nada.
- **Regressão do arranque.** A correção anterior bloqueou os registos P25 feitos durante o `setup()`, porque o SPADE só marca o agente como vivo no fim do `setup()`. Foi detetada pela métrica M10 e corrigida com uma flag própria `stopped`.
- **Perda de mensagens.** Uma pergunta de triagem perdida (5 % de perda em C4) impedia a declaração. Foram acrescentados os retries de F5.
- **Atraso falso.** O ETA de adjudicação era estimado ao centro da célula e marcava estafetas como "atrasados" 1,7 s antes de chegarem. Agora é atualizado com o ETA reportado em P13.
- **Localização perdida após takeover.** A resposta à P24 do novo coordenador perdeu-se, e sem localização não havia realocação: o checker apontou uma violação de OL6. Agora o TRACK volta a pedir a localização enquanto não a tem.
- **Triagem incoerente.** Uma testemunha única com triagem incoerente deixava o P1 sem OS4 e o caso era descartado. Agora o hub volta a fazer as duas perguntas-chave, uma vez (F4), e o prazo da triagem passou para 12 s.
- **Testes instáveis.** Os testes ponta a ponta falhavam de forma intermitente, por variação entre runs. Ficaram estáveis com estas correções (8/8 seguidos) e com um F1 detetável por dois caminhos em C4.

### Próximo: sprint 3

1. **Matriz completa:** `caffeinate -i python experiments/run_matrix.py --matrix main --seeds 1-5 --workers 4`. Demora cerca de 1h40 e tem de correr **ligado à corrente, sem fechar a tampa**. Depois, `python experiments/analyse.py`.
2. **Fonte para a EMS:** confirmar a calibração da EMS (240 s + 30 km/h) com uma fonte, por exemplo dados do INEM.
3. **Opcional:** C5 adversarial e o caminho 112 (A7), para comparar com as linhas de base sobre todos os incidentes.
4. **Entrega:** relatório de desempenho (EN), slides e vídeo da demo a partir do replay no dashboard.

## Primeiro passo após aprovação (feito)

Guardar este plano como `fcup-isia/PLAN.md` e mover o enunciado para `docs/`. Depois arrancar o sprint 0: venv, esqueleto e spike de escala.
