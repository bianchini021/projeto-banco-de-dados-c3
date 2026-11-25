from datetime import datetime


class Relatorio:
    """
    Classe responsável pelos relatórios do Gerenciador de Campeonato de Futebol
    utilizando Aggregation Pipeline nativo do MongoDB (PyMongo).
    """

    def __init__(self, banco):
        # 'banco' deve ser uma instância de pymongo.database.Database
        self.banco = banco

    @staticmethod
    def _formatar_data_utc(valor):
        """
        Exibe a data civil armazenada em UTC sem converter para fuso local,
        conforme regra de integridade (INTEGRIDADE.md).
        """
        if isinstance(valor, datetime):
            return valor.strftime("%d/%m/%Y")
        return str(valor) if valor is not None else "-"

    @staticmethod
    def _imprimir_tabela(titulo, colunas, linhas):
        """Imprime os resultados formatados em tabela no terminal."""
        print(f"\n=== {titulo} ===")
        if not linhas:
            print("Nenhum registro encontrado.")
            return

        larguras = [len(col) for col in colunas]
        for linha in linhas:
            for i, valor in enumerate(linha):
                larguras[i] = max(larguras[i], len(str(valor)))

        separador = "+-" + "-+-".join("-" * w for w in larguras) + "-+"
        cabecalho = "| " + " | ".join(
            str(col).ljust(larguras[i]) for i, col in enumerate(colunas)
        ) + " |"

        print(separador)
        print(cabecalho)
        print(separador)
        for linha in linhas:
            print(
                "| "
                + " | ".join(
                    str(valor).ljust(larguras[i]) for i, valor in enumerate(linha)
                )
                + " |"
            )
        print(separador)

    def get_relatorio_artilharia(self):
        """
        Relatório 1 (Sumarização com $group):
        Soma o total de gols por jogador considerando apenas partidas FINALIZADAS (RN31).
        """
        pipeline = [
            # 1. Cruza GOLS com PARTIDAS para filtrar apenas partidas FINALIZADAS (RN31)
            {
                "$lookup": {
                    "from": "PARTIDAS",
                    "localField": "id_partida",
                    "foreignField": "_id",
                    "as": "partida",
                }
            },
            {"$unwind": "$partida"},
            {"$match": {"partida.status": "FINALIZADA"}},
            # 2. Agrupa por jogador e soma a quantidade de gols ($group)
            {
                "$group": {
                    "_id": "$id_jogador",
                    "total_gols": {"$sum": 1},
                }
            },
            # 3. Busca dados do jogador e do respectivo clube
            {
                "$lookup": {
                    "from": "JOGADORES",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "jogador",
                }
            },
            {"$unwind": "$jogador"},
            {
                "$lookup": {
                    "from": "CLUBES",
                    "localField": "jogador.id_clube",
                    "foreignField": "_id",
                    "as": "clube",
                }
            },
            {"$unwind": "$clube"},
            # 4. Projeta e ordena do maior artilheiro para o menor
            {
                "$project": {
                    "_id": 0,
                    "id_jogador": "$_id",
                    "jogador": "$jogador.nome",
                    "posicao": "$jogador.posicao",
                    "clube": "$clube.nome",
                    "total_gols": 1,
                }
            },
            {"$sort": {"total_gols": -1, "jogador": 1}},
        ]

        resultados = list(self.banco["GOLS"].aggregate(pipeline))
        colunas = ["ID", "Jogador", "Posição", "Clube", "Gols"]
        linhas = [
            [
                doc["id_jogador"],
                doc["jogador"],
                doc["posicao"],
                doc["clube"],
                doc["total_gols"],
            ]
            for doc in resultados
        ]
        self._imprimir_tabela(
            "RELATÓRIO DE ARTILHARIA (PARTIDAS FINALIZADAS)", colunas, linhas
        )
        return resultados

    def get_relatorio_partidas(self):
        """
        Relatório 2 (Junção de coleções com $lookup):
        Lista todas as partidas (ABERTAS e FINALIZADAS - RN32) cruzando com CLUBES.
        """
        pipeline = [
            {
                "$lookup": {
                    "from": "CLUBES",
                    "localField": "id_mandante",
                    "foreignField": "_id",
                    "as": "mandante",
                }
            },
            {"$unwind": "$mandante"},
            {
                "$lookup": {
                    "from": "CLUBES",
                    "localField": "id_visitante",
                    "foreignField": "_id",
                    "as": "visitante",
                }
            },
            {"$unwind": "$visitante"},
            {
                "$project": {
                    "_id": 1,
                    "rodada": 1,
                    "data_partida": 1,
                    "status": 1,
                    "mandante": "$mandante.nome",
                    "gols_mandante": 1,
                    "visitante": "$visitante.nome",
                    "gols_visitante": 1,
                }
            },
            {"$sort": {"rodada": 1, "data_partida": 1, "_id": 1}},
        ]

        resultados = list(self.banco["PARTIDAS"].aggregate(pipeline))
        colunas = ["ID", "Rodada", "Data", "Mandante", "Placar", "Visitante", "Status"]
        linhas = []
        for doc in resultados:
            if doc["status"] == "FINALIZADA":
                placar = f"{doc['gols_mandante']} x {doc['gols_visitante']}"
            else:
                placar = "- x -"
            linhas.append(
                [
                    doc["_id"],
                    doc["rodada"],
                    self._formatar_data_utc(doc["data_partida"]),
                    doc["mandante"],
                    placar,
                    doc["visitante"],
                    doc["status"],
                ]
            )
        self._imprimir_tabela("RELATÓRIO GERAL DE PARTIDAS", colunas, linhas)
        return resultados

    def get_relatorio_gols_detalhados(self):
        """
        Relatório 3 (Junção múltipla com $lookup - bônus):
        Exibe cada gol registrado com partida, rodada, jogador, clube e minuto.
        """
        pipeline = [
            {
                "$lookup": {
                    "from": "PARTIDAS",
                    "localField": "id_partida",
                    "foreignField": "_id",
                    "as": "partida",
                }
            },
            {"$unwind": "$partida"},
            {
                "$lookup": {
                    "from": "JOGADORES",
                    "localField": "id_jogador",
                    "foreignField": "_id",
                    "as": "jogador",
                }
            },
            {"$unwind": "$jogador"},
            {
                "$lookup": {
                    "from": "CLUBES",
                    "localField": "jogador.id_clube",
                    "foreignField": "_id",
                    "as": "clube",
                }
            },
            {"$unwind": "$clube"},
            {
                "$project": {
                    "_id": 1,
                    "id_partida": 1,
                    "rodada": "$partida.rodada",
                    "status_partida": "$partida.status",
                    "jogador": "$jogador.nome",
                    "clube": "$clube.nome",
                    "minuto": 1,
                }
            },
            {"$sort": {"rodada": 1, "id_partida": 1, "minuto": 1, "_id": 1}},
        ]

        resultados = list(self.banco["GOLS"].aggregate(pipeline))
        colunas = ["ID Gol", "Partida", "Rodada", "Jogador", "Clube", "Minuto", "Status"]
        linhas = [
            [
                doc["_id"],
                doc["id_partida"],
                doc["rodada"],
                doc["jogador"],
                doc["clube"],
                f"{doc['minuto']}'",
                doc["status_partida"],
            ]
            for doc in resultados
        ]
        self._imprimir_tabela("RELATÓRIO DE GOLS DETALHADOS", colunas, linhas)
        return resultados