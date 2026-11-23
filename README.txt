RESPOSTA MÉDICA DE EMERGÊNCIA COMUNITÁRIA DESCENTRALIZADA (CEMR)
ISIA 2026/27, trabalho prático 1, tópico O
Rodrigo Dias (202407281) e Francisco Machado (202403514)

Sistema multiagente em SPADE que deteta paragens cardíacas e outros incidentes
urgentes, verifica-os localmente e envia voluntários, DAE e ambulâncias sem
despachante central. A cidade está dividida em células; o armário de DAE de cada
célula é o hub que verifica os alertas e coordena os casos por Contract Net.
O README.md (em inglês) tem a descrição completa.


1. REQUISITOS

- Python 3.10 a 3.14 (testado com 3.13 no Windows e com 3.11 no macOS).
- Nada mais: o servidor XMPP vem embutido no SPADE e arranca sozinho.


2. INSTALAÇÃO

Todos os comandos correm na raiz do projeto (a pasta deste ficheiro).

Windows:
    py -3.13 -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt

macOS / Linux:
    python3.11 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

O requirements.txt instala as dependências com as versões usadas e também o
próprio pacote cemr (linha "-e ."), por isso tem de ser corrido nesta pasta.


3. TESTES

    pytest -m "not slow"     testes unitários (cerca de 3 s)
    pytest                   inclui dois runs SPADE completos (cerca de 2 min)


4. CORRER UMA SIMULAÇÃO

    python -m cemr.run --scenario c4 --seed 1 --duration 1500 --factor 30
        Run curto (cerca de 1 min): o hub 2 falha aos 1200 s e o sucessor
        assume os casos dele.

    python -m cemr.run --scenario c1 --seed 1
        Cenário base: 60 min simulados, cerca de 6 min reais.

    python -m cemr.run --scenario c2 --set sensors.policy=alert_first
        Uma variante: qualquer parâmetro de scenarios/defaults.toml muda com --set.

    python -m cemr.run --scenario c1 --set policy.allocation=naive
        Baseline B1 (difusão ingénua, sem verificação).

Cenários:
    c1  base urbana     densidade média, sensores fiáveis, boa rede
    c2  ruído           falsos positivos x5, sensores com deriva
    c3  pico            8 incidentes em 10 min num raio de 400 m
    c4  periferia       menos voluntários, DAE fechados, falha de um hub
    c5  adversarial     duas pessoas que relatam colapsos falsos

Cada run escreve uma pasta runs/<cenário>-s<seed>-<hora>/ com o audit log
(events.jsonl), os parâmetros (config.json) e as métricas M1-M13
(summary.json). O run é inválido (código de saída 3) se o relógio simulado não
avançou como devia, por exemplo porque o portátil suspendeu: em runs longos,
manter o carregador ligado e a tampa aberta.


5. VERIFICAR AS REGRAS ORGANIZACIONAIS

    python -m cemr.metrics.check runs/<pasta do run> -v

Relê o audit log e confirma as regras da análise Gaia (um só dono por caso, uma
reserva por DAE, divulgação só a quem precisa, entre outras).


6. DEMO (DASHBOARD)

Replay de um run guardado (cenário C4, seed 7), sem correr a simulação:
    python -m cemr.viz.server results/demo/c4-ours-s7
    e abrir http://127.0.0.1:8080/?t=1150&speed=10
O hub 2 cai aos 20:00 simulados e o hub 1 assume os dois casos dele.

Dashboard ao vivo durante um run:
    python -m cemr.run --scenario c1 --factor 5 --viz 8080

Vídeo do mesmo replay: docs/demo_c4_takeover.mp4 (55 s).


7. REPRODUZIR AS EXPERIÊNCIAS

    python experiments/run_matrix.py --matrix main --seeds 1-10 --workers 4
    python experiments/analyse.py

A matriz principal (21 configurações x 10 seeds) demora 6 a 7 horas e recusa
correr com alterações por fazer commit. O analyse.py escreve em results/ as
médias com IC a 95 %, as diferenças emparelhadas por seed e as figuras. Os
números do relatório e dos slides vêm de results/ (210 runs, commit de13290).


8. ONDE ESTÁ O QUÊ

    src/cemr/         código (agentes, protocolos, ambiente, métricas, dashboard)
    tests/            testes unitários e end-to-end
    scenarios/        parâmetros (defaults.toml, documentado) e cenários C1-C5
    experiments/      scripts da matriz de experiências e da análise
    results/          resultados da matriz final e run da demo
    docs/             análise Gaia, desenho arquitetural, desenho detalhado,
                      protocolos e esquemas das mensagens
    report/           relatório de desempenho (relatorio.pdf; fonte LaTeX em main.tex)
    slides/           apresentação (apresentacao.pdf) e guião (guiao.md)
