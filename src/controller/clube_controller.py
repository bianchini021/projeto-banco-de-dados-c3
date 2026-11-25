from pymongo.errors import DuplicateKeyError

from src.controller.validacoes import exigir_colecoes, proximo_id, texto
from src.model.clube import Clube
from src.utils.database import MongoQueries


class ClubeController:
    def cadastrar_clube(self, nome, cidade=None):
        nome = texto(nome, "nome", 100)
        cidade = texto(cidade, "cidade", 80, obrigatorio=False)
        conexao = MongoQueries()
        try:
            banco = conexao.connect()
            exigir_colecoes(banco, "CLUBES")
            colecao = banco["CLUBES"]
            try:
                colecao.create_index("nome", unique=True)
            except DuplicateKeyError:
                raise ValueError("Há nomes de clubes duplicados na base. "
                                 "O cadastro foi interrompido sem alterar documentos.") from None
            if colecao.find_one({"nome": nome}) is not None:
                raise ValueError("Já existe um clube com esse nome.")

            clube = Clube(proximo_id(colecao), nome, cidade)
            documento = {
                "_id": clube.get_id_clube(),
                "nome": clube.get_nome(),
                "cidade": clube.get_cidade(),
            }
            try:
                resultado = colecao.insert_one(documento)
            except DuplicateKeyError:
                raise ValueError("O ID ou nome do clube já foi cadastrado. "
                                 "Confira os dados e tente novamente.") from None
            return resultado.inserted_id
        finally:
            conexao.close()
