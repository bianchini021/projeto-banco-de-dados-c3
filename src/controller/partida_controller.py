from datetime import date, datetime, timezone

from pymongo.errors import DuplicateKeyError

from src.controller.validacoes import exigir_colecoes, inteiro, proximo_id
from src.model.clube import Clube
from src.model.partida import Partida
from src.utils.database import MongoQueries


def validar_data(valor):
    if isinstance(valor, datetime):
        raise ValueError("Informe apenas a data, sem horário.")
    if isinstance(valor, str):
        valor = valor.strip()
        try:
            dia = date.fromisoformat(valor)
        except ValueError:
            raise ValueError("Data inválida. Use AAAA-MM-DD.") from None
        if dia.isoformat() != valor:
            raise ValueError("Data inválida. Use AAAA-MM-DD.")
    elif isinstance(valor, date):
        dia = valor
    else:
        raise ValueError("Data inválida. Use AAAA-MM-DD.")
    return datetime(dia.year, dia.month, dia.day, tzinfo=timezone.utc)


class PartidaController:
    def cadastrar_partida(self, id_mandante, id_visitante, rodada, data_partida):
        id_mandante = inteiro(id_mandante, "id_mandante")
        id_visitante = inteiro(id_visitante, "id_visitante")
        rodada = inteiro(rodada, "rodada")
        data_partida = validar_data(data_partida)
        if id_mandante == id_visitante:
            raise ValueError("Mandante e visitante devem ser diferentes.")
        conexao = MongoQueries()
        try:
            banco = conexao.connect()
            exigir_colecoes(banco, "CLUBES", "PARTIDAS")
            mandante = banco["CLUBES"].find_one({"_id": id_mandante})
            visitante = banco["CLUBES"].find_one({"_id": id_visitante})
            if mandante is None or visitante is None:
                raise ValueError("Mandante e visitante devem ser clubes cadastrados.")
            colecao = banco["PARTIDAS"]
            confronto = colecao.find_one({
                "rodada": rodada,
                "$or": [
                    {"id_mandante": id_mandante, "id_visitante": id_visitante},
                    {"id_mandante": id_visitante, "id_visitante": id_mandante},
                ],
            })
            if confronto is not None:
                raise ValueError("Esses clubes já possuem uma partida nesta rodada.")
            partida = Partida(
                proximo_id(colecao),
                Clube(mandante["_id"], mandante["nome"], mandante["cidade"]),
                Clube(visitante["_id"], visitante["nome"], visitante["cidade"]),
                rodada, data_partida,
            )
            documento = {
                "_id": partida.get_id_partida(),
                "id_mandante": partida.get_id_mandante(),
                "id_visitante": partida.get_id_visitante(),
                "rodada": partida.get_rodada(),
                "data_partida": partida.get_data_partida(),
                "status": "ABERTA",
                "gols_mandante": None,
                "gols_visitante": None,
            }
            try:
                resultado = colecao.insert_one(documento)
            except DuplicateKeyError:
                raise ValueError("O ID da partida já foi cadastrado. Tente novamente.") from None
            return resultado.inserted_id
        finally:
            conexao.close()
