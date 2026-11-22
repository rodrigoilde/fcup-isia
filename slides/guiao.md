# Guião da apresentação (CEMR, ISIA 2026/27)

Gerado com os slides em `apresentacao.pptx`; o mesmo texto está nas notas do orador.
Os números vêm da matriz final: 210 runs válidos no commit `de13290` (`results/summary.md`, `results/paired.md`).
Tempo total previsto: 9 min 10 s (limite: 10 min). Se o ensaio passar do tempo, cortar primeiro a frase sobre as arquiteturas no slide 3 e a das regras por construção no mesmo slide.

## Slide 1 · Título (0:20)

Bom dia. Somos o Rodrigo Dias e o Francisco Machado. O nosso tópico é a resposta médica de emergência comunitária sem despachante central. Vamos mostrar o problema, como desenhámos o sistema multiagente em SPADE e o que medimos em 210 simulações.

## Slide 2 · Numa paragem cardíaca, o que conta acontece antes de a ambulância chegar (1:00)

O caso mais exigente é a paragem cardiorrespiratória fora do hospital. Sem ninguém a intervir, a sobrevivência cai cerca de 5,5 pontos percentuais por minuto, segundo o modelo de Larsen que também usamos na métrica M6. Na nossa simulação, a ambulância chega em média aos 6 minutos e meio na cidade e quase aos 13 na periferia; é esse intervalo que queremos ocupar com voluntários e DAE próximos. Já existem sistemas de voluntários, nos Países Baixos e na Escandinávia, mas com despacho central. O enunciado pede o contrário: nenhum agente vê a cidade toda. Isto dá quatro tarefas, que na análise Gaia são quatro sub-organizações: detetar e verificar, despachar, guiar a testemunha e proteger os dados.

## Slide 3 · Cada armário de DAE é o hub da sua célula; os hubs coordenam-se como pares (1:00)

Dividimos a cidade em células à volta dos armários de DAE, que são infraestrutura fixa, com energia e rede. Cada armário é o hub da sua célula: verifica alertas, coordena o caso, guarda o DAE e mantém a reputação das fontes. Os hubs vizinhos são pares e nenhum está acima dos outros. Os restantes agentes vivem nos telemóveis e na ambulância. O hub é um agente híbrido em camadas; o voluntário e a ambulância são agentes baseados em utilidade, e o dispositivo é um agente reflexo com modelo. Com esta estrutura, três regras da análise valem por construção: um só dono por caso, quem alerta não verifica, e só coordenam agentes provisionados.

## Slide 4 · Um caso passa por cinco fases, cada uma assente em protocolos FIPA (1:15)

Este é o percurso de um caso P1. O dispositivo ou a testemunha alerta o hub da sua célula (P01). O hub pergunta à vizinhança e faz a triagem à testemunha (P03, P04); quando a evidência chega ao limiar, declara o incidente (P06). Pede a ambulância (P10) e chama voluntários com um Contract Net: cfp, propostas, adjudicação (P08, P09). O voluntário que vai buscar o DAE reserva-o e levanta-o com o token da adjudicação (P11, P12). Todos reportam o estado (P13), a EMS recebe a passagem do caso (P19) e o hub fecha-o e envia o resultado para a reputação (P20, P21). Os 28 protocolos usam padrões FIPA conhecidos e o envelope FIPA-ACL. À direita está uma adjudicação P09 real: a metadata da mensagem, com o id do caso como thread, e o corpo em JSON.

## Slide 5 · O hub declara por fusão bayesiana e reputação; aloca por Contract Net (1:15)

Dentro do hub, cada caso é uma FSMBehaviour do SPADE: verificar, despachar, acompanhar e fechar, ou descartar. A decisão individual é declarar ou não: uma fusão bayesiana em log-odds, em que cada evidência pesa pela confiança na fonte, dada por um modelo de reputação Beta partilhado entre hubs. A decisão coletiva tem duas partes. A alocação é um Contract Net, que funciona como um leilão reverso selado: o lance é o ETA calculado no telemóvel do voluntário e ganha a menor pontuação. Não é um Vickrey, porque não há pagamentos; quem declara um ETA falso perde reputação. A outra parte é a prioridade do caso quando as fontes discordam. Na tabela, três fontes dizem P3 e uma diz P1: pluralidade, Borda e Condorcet dão P3, e nós escolhemos P1. Perdemos o critério de Condorcet de propósito, porque tratar uma paragem como um caso leve custa muito mais do que o contrário.

## Slide 6 · Registo por célula, privacidade e recuperação de falhas completam o sistema (0:50)

Quatro mecanismos completam o sistema. A descoberta funciona como páginas amarelas por célula: voluntários e testemunhas subscrevem os hubs próximos e dizem só a célula. A localização exata fica no telemóvel e só sai, a pedido, para quem foi adjudicado; os dados clínicos só vão para a EMS. Se um hub falha, o sucessor, que tem uma réplica de cada caso, assume quando deixam de chegar heartbeats. Por fim, o ambiente injeta latência, perdas e zonas sem rede, e um verificador relê o audit log de cada run e confirma as regras organizacionais.

## Slide 7 · Avaliámos 21 configurações em 5 cenários contrastantes, com 10 seeds cada (0:45)

Avaliámos cinco cenários contrastantes: base urbana, ruído e falsos alarmes, um pico de incidentes num evento, uma periferia degradada com o crash de um hub e fontes adversárias, com duas pessoas que inventam colapsos. Em todos comparamos com a difusão ingénua, B1, e medimos a distância a um oráculo centralizado, B0. Com as variantes são 21 configurações, cada uma com 10 seeds: 210 runs válidos de 60 minutos simulados, todos do mesmo commit.

## Slide 8 · A RCP começa 2 a 6 vezes mais cedo do que com B1; o ganho vem sobretudo da guia da testemunha (1:00)

O resultado principal é o tempo até à RCP. Nos cinco cenários, o nosso sistema põe alguém a fazer RCP em menos de 3 minutos, e na cidade em menos de 1. Com a difusão ingénua demora entre 4 minutos e meio e 6 minutos e meio. A barra cinzenta é a mesma coordenação sem a guia da testemunha, e fica perto de B1: quase todo o ganho vem de a testemunha começar a RCP guiada pelo telemóvel, e não do Contract Net. Comparando por seed, a coordenação sozinha só encurta a RCP de forma clara em C1, cerca de 55 segundos. O proxy de sobrevivência de Larsen vai no mesmo sentido: de 31 para 42 % na cidade e de 9 para 16 % na periferia.

## Slide 9 · O ganho tem custos: verificar atrasa, há mais mensagens e k = 3 expõe mais a localização (1:00)

Este ganho tem custos. Verificar antes de enviar atrasa a declaração 7 a 14 segundos face a B1, e o Contract Net troca até mais 49 % de mensagens por candidato. Em troca, cada voluntário recebe menos alertas. Com ruído, a precisão fica igual à de B1, mas os falsos despachos caem para metade. AlertFirst e ConfirmFirst dão a mesma precisão, e AlertFirst gasta menos mensagens; a diferença de latência fica dentro do intervalo de confiança. Com fontes adversárias, a reputação corta os falsos despachos para menos de metade. Em C3, k = 3 aproxima-nos do oráculo, mas o intervalo inclui zero, e a localização chega a quase o dobro dos agentes. Em C4, o sucessor assume os casos do hub que caiu em cerca de 21 segundos, sem casos órfãos.

## Slide 10 · A guia da testemunha leva a RCP mais cedo ao doente; a reputação trava fontes adversárias (0:45)

Concluímos que o sistema chega ao doente mais cedo do que a difusão ingénua e que a maior parte do ganho vem da guia da testemunha. A reputação trava quem repete relatos falsos, e a configuração principal cumpre as regras organizacionais nos 50 runs. A limitação principal são os casos duplicados entre células, que aparecem com perda de mensagens e na variante sem guia do C4, a par do modelo sintético da cidade. Como trabalho futuro, queremos esperar pela resposta P26 antes de declarar, reenviar a guia que se perde e acrescentar o caminho 112. Obrigado; ficamos para as perguntas.

## Slides de backup

Não fazem parte dos 10 minutos. Servem para responder a perguntas:

- B1. C1: mesma precisão que B1, RCP 6× mais cedo e metade dos alertas por voluntário
- B2. C2: metade dos falsos despachos de B1; as variantes do sensor quase não mudam os resultados
- B3. C3: k = 1, 2 ou 3 dão o mesmo tempo até RCP; k muda sobretudo mensagens e exposição
- B4. C4: na periferia, RCP em ~3 min contra ~6 min com B1
- B5. C5: a reputação corta para menos de metade os falsos despachos de fontes adversárias
- B6. Missões do voluntário e da ambulância, e o que o hub faz em cada estado
- B7. Calibração da fusão: os alvos de declaração e descarte que os parâmetros cumprem
- B8. Os 15 modos de falha da análise e como cada um é tratado
- B9. Evolução do desenho: cada correção medida nas mesmas seeds, antes e depois (`results/evolution.md`, docs/03 §7.1). A fusão por área subiu o recall de C3 de 64,0 para 77,5 %; repetir a triagem que contradiz o relato subiu-o de 75,8 para 80,3 %; contar a mesma fonte uma só vez não teve efeito medível em C5.
- B10. Demo: replay do run C4 (seed 7) guardado em `results/demo/c4-ours-s7`, que não precisa de XMPP nem de correr a simulação. Comando: `python -m cemr.viz.server results/demo/c4-ours-s7` e abrir `http://127.0.0.1:8080/?t=1150&speed=10`. O hub2 cai aos 1200 s e o hub1 assume os dois casos dele em 19,6 s. Se o portátil falhar, passa-se o vídeo desse replay, `docs/demo_c4_takeover.mp4` (55 s; o takeover aparece aos 0:14).
