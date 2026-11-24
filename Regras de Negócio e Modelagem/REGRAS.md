# Regras de negócio - Gerenciador de Campeonato de Futebol

As regras da C3 mantêm o tema e o escopo definidos na C2, utilizando MongoDB como banco da aplicação.

## 1. Escopo do campeonato

- RN01: Cada base representa um único campeonato, sem uma coleção adicional de campeonatos.
- RN02: O campeonato possui clubes, jogadores, partidas e gols.
- RN03: Transferências de jogadores, múltiplas temporadas, gols contra e disputas de pênaltis ficam fora do escopo.

## 2. Clubes

- RN04: Cada clube deve possuir um nome obrigatório e único. Nomes vazios ou compostos apenas por espaços não são permitidos.
- RN05: A cidade do clube é opcional.
- RN06: Um clube pode possuir nenhum ou vários jogadores e participar de nenhuma ou várias partidas.

## 3. Jogadores

- RN07: Cada jogador deve possuir nome e posição e pertencer a exatamente um clube cadastrado.
- RN08: As posições permitidas são Goleiro, Zagueiro, Lateral, Volante, Meio-Campo e Atacante.
- RN09: O clube de um jogador com gols registrados não pode ser alterado, preservando o histórico dos gols.

## 4. Partidas

- RN10: Cada partida deve possuir um clube mandante, um clube visitante, uma rodada e uma data.
- RN11: Mandante e visitante devem ser clubes cadastrados e diferentes entre si.
- RN12: A rodada deve ser um número inteiro maior que zero, e a data representa apenas o dia da partida, sem horário.
- RN13: O mesmo par de clubes não pode disputar duas partidas na mesma rodada, mesmo com o mando invertido.
- RN14: Uma partida pode ter apenas os estados ABERTA e FINALIZADA. O estado inicial é ABERTA.
- RN15: Uma partida ABERTA deve manter os dois campos de placar nulos, mesmo que já existam gols registrados.
- RN16: Uma partida FINALIZADA deve possuir os dois placares preenchidos com inteiros não negativos. O resultado 0 a 0 é permitido.

## 5. Gols

- RN17: Cada gol deve estar associado a uma partida existente e a um jogador existente.
- RN18: O jogador que marcou o gol deve pertencer a um dos clubes participantes da partida.
- RN19: Um jogador pode marcar vários gols na mesma partida, inclusive no mesmo minuto. Cada gol possui seu próprio identificador.
- RN20: O minuto deve ser um inteiro entre 1 e 130. Acréscimos são registrados como minutos absolutos: 45+2 corresponde a 47.
- RN21: Gols só podem ser cadastrados, alterados ou excluídos em partidas ABERTAS. Ao mover um gol entre partidas, ambas devem estar abertas e as associações devem continuar válidas.

## 6. Finalização e correções

- RN22: Para finalizar uma partida, contar os gols de cada clube com base no clube do jogador que marcou.
- RN23: Os dois placares e o estado FINALIZADA devem ser atualizados juntos. Os placares finais devem corresponder aos gols registrados.
- RN24: Para corrigir gols de uma partida FINALIZADA, reabrir a partida antes da alteração, definir os dois placares como nulos e preservar os gols já cadastrados.
- RN25: Após a correção, finalizar novamente a partida para recalcular os placares.
- RN26: Alterações nos clubes de uma partida não podem invalidar a associação dos gols já registrados.

## 7. Exclusões

- RN27: Solicitar confirmação antes de excluir um registro.
- RN28: Bloquear a exclusão de um clube que possua jogadores ou participe de partidas, como mandante ou visitante.
- RN29: Bloquear a exclusão de um jogador ou de uma partida que possua gols associados.
- RN30: Não haverá exclusão automática em cascata. Informar ao usuário quais relacionamentos impedem a exclusão.

## 8. Relatórios

- RN31: Relatórios de resultados e artilharia devem considerar apenas partidas FINALIZADAS.
- RN32: A listagem geral de partidas pode apresentar partidas ABERTAS e FINALIZADAS, exibindo o estado de cada uma.

## 9. Aplicação das regras

Este documento define o comportamento esperado. Ele não significa que todos os CRUDs e relatórios já estejam implementados. A situação das validações existentes e os requisitos de integridade estão descritos em [INTEGRIDADE.md](INTEGRIDADE.md).
