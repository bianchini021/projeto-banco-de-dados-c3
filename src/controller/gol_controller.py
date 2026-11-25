from pymongo.errors import DuplicateKeyError

from src.controller.validacoes import exigir_colecoes, inteiro, proximo_id
from src.model.clube import Clube
from src.model.gol import Gol
from src.model.jogador import Jogador
from src.model.partida import Partida
from src.utils.database import MongoQueries


class GolController:
    def cadastrar_gol(self, id_partida, id_jogador, minuto):
        id_partida = inteiro(id_partida, "id_partida")
        id_jogador = inteiro(id_jogador, "id_jogador")
        minuto = inteiro(minuto, "minuto", maximo=130)
        conexao = MongoQueries()
        try:
            banco = conexao.connect()
            exigir_colecoes(banco, "CLUBES", "JOGADORES", "PARTIDAS", "GOLS")
            registro_partida = banco["PARTIDAS"].find_one({"_id": id_partida})
            if registro_partida is None:
                raise ValueError("A partida informada não existe.")
            if registro_partida["status"] != "ABERTA":
                raise ValueError("Gols só podem ser cadastrados em partidas ABERTAS.")
            if (registro_partida["gols_mandante"] is not None
                    or registro_partida["gols_visitante"] is not None):
                raise ValueError("A partida aberta possui placar inconsistente.")
            registro_jogador = banco["JOGADORES"].find_one({"_id": id_jogador})
            if registro_jogador is None:
                raise ValueError("O jogador informado não existe.")
            id_mandante = registro_partida["id_mandante"]
            id_visitante = registro_partida["id_visitante"]
            if id_mandante == id_visitante:
                raise ValueError("A partida possui clubes iguais e precisa ser corrigida.")
            if registro_jogador["id_clube"] not in (id_mandante, id_visitante):
                raise ValueError("O jogador não pertence a um dos clubes da partida.")
            mandante = banco["CLUBES"].find_one({"_id": id_mandante})
            visitante = banco["CLUBES"].find_one({"_id": id_visitante})
            if mandante is None or visitante is None:
                raise ValueError("Um dos clubes da partida não existe.")
            mandante = Clube(mandante["_id"], mandante["nome"], mandante["cidade"])
            visitante = Clube(visitante["_id"], visitante["nome"], visitante["cidade"])
            partida = Partida(id_partida, mandante, visitante,
                              registro_partida["rodada"], registro_partida["data_partida"])
            clube = mandante if registro_jogador["id_clube"] == id_mandante else visitante
            jogador = Jogador(id_jogador, registro_jogador["nome"], registro_jogador["posicao"], clube)
            colecao = banco["GOLS"]
            gol = Gol(proximo_id(colecao), partida, jogador, minuto)
            documento = {
                "_id": gol.get_id_gol(),
                "id_partida": gol.get_id_partida(),
                "id_jogador": gol.get_id_jogador(),
                "minuto": gol.get_minuto(),
            }
            try:
                resultado = colecao.insert_one(documento)
            except DuplicateKeyError:
                raise ValueError("O ID do gol já foi cadastrado. Tente novamente.") from None
            return resultado.inserted_id
        finally:
            conexao.close()
