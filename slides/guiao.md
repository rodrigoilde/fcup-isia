# Guião da apresentação (CEMR, ISIA 2026/27)

Gerado com os slides em `apresentacao.pptx`; o mesmo texto está nas notas do orador.
Tempo total previsto: 9 min 50 s (limite: 10 min). Se o ensaio passar do tempo, cortar primeiro a frase sobre Russell e Norvig no slide 5 e a comparação de estruturas no slide 3.

## Slide 1 · Título (0:20)

Bom dia. Somos [nomes do grupo]. O nosso tópico é a resposta médica de emergência comunitária sem despachante central. Vamos mostrar o problema, como desenhámos o sistema multiagente em SPADE e o que medimos em 65 simulações.

## Slide 2 · Numa paragem cardíaca, o que conta acontece antes de a ambulância chegar (1:00)

O caso mais exigente é a paragem cardiorrespiratória fora do hospital. Sem RCP nem desfibrilhação, a probabilidade de sobreviver cai 7 a 10 % por minuto. Na nossa simulação, a ambulância chega em média aos 6 minutos na cidade e aos 12 na periferia; é esse intervalo que queremos ocupar com voluntários e DAE próximos. Já existem sistemas de voluntários, nos Países Baixos e na Escandinávia, mas com despacho central. O enunciado pede o contrário: nenhum agente vê a cidade toda. Isto dá quatro tarefas, que na análise Gaia são quatro sub-organizações: detetar e verificar, despachar, guiar a testemunha e proteger os dados.

## Slide 3 · Cada armário de DAE é o hub da sua célula; os hubs coordenam-se como pares (1:15)

Dividimos a cidade em células à volta dos armários de DAE, que são infraestrutura fixa, com energia e rede. Cada armário é o hub da sua célula: verifica alertas, coordena o caso, guarda o DAE e mantém a reputação das fontes. Os hubs vizinhos são pares e nenhum está acima dos outros. Os restantes agentes vivem nos telemóveis e na ambulância: o dispositivo do cidadão com o sensor, a testemunha, o voluntário e a EMS. Escolhemos esta estrutura porque três regras da análise passam a valer por construção: um só dono por caso (OS1), quem alerta não verifica (OS7) e só coordenam agentes provisionados (OS13). Comparámos com um coletivo de pares e com um coordenador efémero por caso; as duas alternativas precisavam de consenso ou de eleição em cada caso.

## Slide 4 · Um caso passa por cinco fases, cada uma assente em protocolos FIPA (1:15)

Este é o percurso de um caso P1. O dispositivo ou a testemunha alerta o hub da sua célula (P01). O hub pergunta à vizinhança e faz a triagem à testemunha (P03, P04); quando a evidência chega ao limiar, declara o incidente (P06). Pede a ambulância (P10) e chama voluntários com um Contract Net: cfp, propostas, adjudicação (P08, P09). O voluntário que vai buscar o DAE reserva-o e levanta-o com o token da adjudicação (P11, P12). Todos reportam o estado (P13), a EMS recebe a passagem do caso (P19) e o hub fecha-o e envia o resultado para a reputação (P20, P21). Os 28 protocolos usam padrões FIPA conhecidos e o envelope FIPA-ACL. O thread da mensagem é o id do caso, e um número de sequência torna os reenvios idempotentes.

## Slide 5 · O hub declara por fusão bayesiana e reputação; aloca por Contract Net (1:15)

Dentro do hub, cada caso é uma FSMBehaviour do SPADE: verificar, despachar, acompanhar e fechar, ou descartar. A decisão de declarar é uma fusão bayesiana em log-odds, em que cada evidência pesa pela confiança na fonte. Essa confiança vem de um modelo de reputação Beta, partilhado entre hubs vizinhos por gossip. A decisão coletiva é a alocação: um Contract Net em que cada voluntário calcula o seu ETA no telemóvel e o hub ordena as propostas por ETA, qualificação e confiança. Usamos redundância controlada: num P1, dois voluntários para RCP e um para o DAE. Nos tipos de Russell e Norvig, o hub e o voluntário são baseados em utilidade, o dispositivo é reflexo com modelo, a guia da testemunha é reflexo simples e a EMS é baseada em objetivos. Não usamos BDI; tudo são behaviours do SPADE.

[A VALIDAR PELO GRUPO: a classificação de Russell e Norvig é uma proposta e ainda não está escrita nas docstrings dos agentes.]

## Slide 6 · Registo por célula, privacidade e recuperação de falhas completam o sistema (1:15)

Quatro mecanismos completam o sistema. A descoberta funciona como páginas amarelas por célula: voluntários e testemunhas subscrevem os hubs próximos e dizem só a célula, nunca a posição. A localização exata fica no telemóvel do titular e só sai, a pedido do coordenador, dentro da adjudicação; os dados clínicos só vão para a EMS e tudo é purgado depois do fecho. Para a falha de um hub, o dono replica cada caso para um sucessor fixo e envia heartbeats; sem heartbeat, o sucessor assume o caso. Por fim, o ambiente simulado injeta latência, perdas e zonas sem rede, e um verificador relê o audit log de cada run e confirma as regras organizacionais.

## Slide 7 · Avaliámos 13 configurações em 4 cenários contrastantes, com 5 seeds cada (0:45)

Avaliámos quatro cenários contrastantes: base urbana, ruído e falsos alarmes, um pico de incidentes num evento e uma periferia degradada com o crash de um hub. Em todos comparamos com a difusão ingénua, B1, e medimos a distância a um oráculo centralizado, B0. Com as variantes de C2 e C3 são 13 configurações, cada uma com 5 seeds: 65 runs válidos de 60 minutos simulados.

## Slide 8 · Com Contract Net, a RCP começa 3 a 8 vezes mais cedo do que com difusão ingénua (1:00)

O resultado principal é o tempo até à RCP. Nos quatro cenários, o nosso sistema põe alguém a fazer RCP em cerca de um minuto, entre 56 e 90 segundos. Com a difusão ingénua demora entre 4 e 8 minutos, porque os voluntários aceitam sem coordenação: vários vão para o mesmo caso e outros chegam tarde. O proxy de sobrevivência de Larsen vai no mesmo sentido: de 34 para 44 % na cidade e de 12 para 23 % na periferia. São médias de 5 seeds e alguns intervalos são largos, por isso falamos de ordem de grandeza e não de valores exatos.

## Slide 9 · O ganho tem custos: verificar atrasa, há mais mensagens e k = 3 expõe mais a localização (1:00)

Este ganho tem custos. Verificar antes de enviar atrasa a declaração cerca de 9 segundos face a B1, e o Contract Net troca mais mensagens. Em troca, cada voluntário recebe menos alertas. No cenário de ruído, a precisão é maior do que em B1, mas os intervalos sobrepõem-se. AlertFirst e ConfirmFirst dão a mesma precisão, e AlertFirst é mais rápido e mais barato. Desligar a reputação não mudou nada mensurável: em 60 minutos há poucas observações por fonte. Em C3, mais redundância aproxima-nos do oráculo, mas a localização chega a mais agentes. Em C4, depois do crash de um hub, o sucessor assume o caso em cerca de 19 segundos, e o verificador não encontrou dois donos em nenhum run.

## Slide 10 · A coordenação por células chega mais cedo ao doente; a reputação ainda não mostrou efeito (0:45)

Concluímos que a coordenação local, por células, chega ao doente mais cedo do que a difusão ingénua e cumpre as regras de privacidade e de exclusividade em todos os runs. As limitações principais são o custo em latência e em mensagens, a reputação sem efeito visível e o modelo sintético da cidade. Como trabalho futuro, queremos o cenário adversarial, o caminho 112 e runs mais longos. Obrigado; ficamos para as perguntas.

## Slides de backup

Não fazem parte dos 10 minutos. Servem para responder a perguntas:

- B1. C1: mesma precisão que B1, RCP 4× mais cedo e menos alertas por voluntário
- B2. C2: as variantes do sensor e a reputação quase não mudam os resultados
- B3. C3: k = 1, 2 ou 3 dão o mesmo tempo até RCP; k muda sobretudo mensagens e exposição
- B4. C4: na periferia, RCP em ~1 min contra ~8 min com B1
- B5. Missões do voluntário e da ambulância, e o que o hub faz em cada estado
- B6. Calibração da fusão: os alvos de declaração e descarte que os parâmetros cumprem
- B7. Os 15 modos de falha da análise e como cada um é tratado
- B8. Demo: o dashboard mostra células, agentes, mensagens e métricas ao vivo ou em replay
