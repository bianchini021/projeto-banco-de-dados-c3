# Regras de integridade - Gerenciador de Campeonato de Futebol

Este documento complementa [REGRAS.md](REGRAS.md) e o [diagrama relacional](diagrama_relacional.mmd), definindo o contrato dos dados e as validações necessárias na migração e na aplicação MongoDB.

## 1. Integridade de entidade

- Cada registro possui um identificador inteiro positivo e único dentro de sua entidade.
- No Oracle, os identificadores são as chaves primárias `id_clube`, `id_jogador`, `id_partida` e `id_gol`, geradas por IDENTITY.
- Na migração para MongoDB, a chave primária de cada registro passa a ser `_id`, preservando seu valor numérico.
- As referências mantêm os nomes e os valores originais. Por exemplo, `JOGADORES.id_clube` referencia `CLUBES._id`.
- Um documento não deve repetir sua chave primária em outro campo: CLUBES possui `_id`, não `_id` e `id_clube` simultaneamente.
- O identificador de um registro existente não deve ser alterado nas atualizações.
- Novos cadastros devem gerar IDs sem colisão com os registros migrados. A geração de novos IDs pertence ao módulo de inserção e ainda precisa ser integrada.

## 2. Integridade de domínio

Todos os campos apresentados abaixo devem existir no documento. Os campos opcionais admitem `null`.

| Entidade | Campo | Restrição |
|---|---|---|
| Todas | `_id` | Inteiro positivo e único na coleção |
| CLUBES | `nome` | Texto obrigatório, até 100 caracteres, único e não composto apenas por espaços |
| CLUBES | `cidade` | Texto de até 80 caracteres ou `null` |
| JOGADORES | `nome` | Texto obrigatório, até 100 caracteres, não composto apenas por espaços |
| JOGADORES | `posicao` | Goleiro, Zagueiro, Lateral, Volante, Meio-Campo ou Atacante |
| JOGADORES | `id_clube` | Inteiro positivo; clube existente |
| PARTIDAS | `id_mandante`, `id_visitante` | Inteiros positivos; clubes existentes e diferentes entre si |
| PARTIDAS | `rodada` | Inteiro maior que zero |
| PARTIDAS | `data_partida` | Data obrigatória, sem horário; BSON Date à meia-noite UTC |
| PARTIDAS | `status` | ABERTA ou FINALIZADA |
| PARTIDAS | `gols_mandante`, `gols_visitante` | Ambos `null` em ABERTA; ambos inteiros não negativos em FINALIZADA |
| GOLS | `id_partida` | Inteiro positivo; partida existente |
| GOLS | `id_jogador` | Inteiro positivo; jogador existente |
| GOLS | `minuto` | Inteiro entre 1 e 130 |

Os inteiros migrados devem caber no intervalo BSON de 64 bits com sinal: até `9223372036854775807`. Booleanos, textos numéricos e números fracionários não substituem inteiros. A migração rejeita conversões de ponto flutuante com precisão insegura.

O modelo preserva a data civil da C2. Ao exibir uma data, manter o dia armazenado, sem convertê-lo para o fuso local. Campos adicionais exigem revisão deste contrato e da migração, pois o script atual rejeita campos diferentes dos definidos no modelo.

## 3. Integridade referencial

| Entidade referenciada | Referência dependente | Regra |
|---|---|---|
| CLUBES | JOGADORES.id_clube | O clube deve existir antes do jogador; sua exclusão fica bloqueada enquanto houver jogadores |
| CLUBES | PARTIDAS.id_mandante | O clube deve existir antes da partida; sua exclusão fica bloqueada enquanto houver partidas como mandante |
| CLUBES | PARTIDAS.id_visitante | O clube deve existir antes da partida; sua exclusão fica bloqueada enquanto houver partidas como visitante |
| PARTIDAS | GOLS.id_partida | A partida deve existir antes do gol; sua exclusão fica bloqueada enquanto houver gols |
| JOGADORES | GOLS.id_jogador | O jogador deve existir antes do gol; sua exclusão fica bloqueada enquanto houver gols |

As referências são obrigatórias. Um clube, jogador ou partida pode não possuir registros dependentes. Cada jogador possui um clube; cada partida possui um mandante e um visitante; cada gol possui uma partida e um jogador.

O schema Oracle declara as chaves estrangeiras e não utiliza exclusão em cascata. No MongoDB, essas referências precisam ser verificadas pela aplicação; a migração não instala constraints de chave estrangeira.

## 4. Integridade entre registros

- A existência do jogador e da partida não basta para cadastrar um gol: o clube do jogador também deve participar da partida.
- O par de clubes e a rodada devem ser verificados para impedir confrontos repetidos, considerando o mando invertido.
- Alterar o clube de um jogador com gols registrados deve ser bloqueado para preservar o histórico.
- Alterar os clubes de uma partida deve preservar a validade dos gols associados.
- O placar de uma partida FINALIZADA deve ser igual à contagem dos gols de cada clube.
- Para corrigir gols de uma partida finalizada, seguir o fluxo de reabertura definido nas regras de negócio.
- Antes de atualizar ou excluir, confirmar que o registro existe. Antes de inserir, verificar referências e unicidade. As verificações precisam ser repetidas quando uma atualização alterar esses vínculos.

## 5. Integridade na migração

- Ler as quatro tabelas Oracle em uma transação somente de leitura.
- Criar as coleções CLUBES, JOGADORES, PARTIDAS e GOLS, mantendo os nomes das tabelas Oracle.
- Preservar identificadores, referências, textos, datas e estados, realizando apenas as conversões necessárias de tipos.
- Validar a origem e a união com os documentos existentes antes da primeira escrita.
- Reaproveitar um documento existente somente quando possuir o mesmo ID e os mesmos dados; conflitos devem interromper a migração.
- Inserir na ordem CLUBES, JOGADORES, PARTIDAS e GOLS, preservando as dependências.
- A simulação não deve criar coleções nem inserir documentos.
- A reaplicação de uma carga idêntica não deve duplicar documentos nem sobrescrever registros diferentes.
- Durante a migração, manter a aplicação parada e impedir outras escritas no destino.
- Uma falha pode deixar inserções parciais. Corrigir a causa e executar a simulação antes de retomar a aplicação da carga.

O schema Oracle adapta a estrutura da C2, originalmente PostgreSQL. Ele cria tabelas, mas não transfere os dados antigos do PostgreSQL para o Oracle.