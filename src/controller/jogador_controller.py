from pymongo.errors import DuplicateKeyError

from src.controller.validacoes import exigir_colecoes, inteiro, proximo_id, texto
from src.model.clube import Clube
from src.model.jogador import Jogador
from src.utils.database import MongoQueries


POSICOES = ("Goleiro", "Zagueiro", "Lateral", "Volante", "Meio-Campo", "Atacante")


class JogadorController:
    def cadastrar_jogador(self, nome, posicao, id_clube):
        nome = texto(nome, "nome", 100)
        posicao = texto(posicao, "posição", 20)
        if posicao not in POSICOES:
            raise ValueError("Posição inválida. Opções: " + ", ".join(POSICOES))
        id_clube = inteiro(id_clube, "id_clube")
        conexao = MongoQueries()
        try:
            banco = conexao.connect()
            exigir_colecoes(banco, "CLUBES", "JOGADORES")
            registro = banco["CLUBES"].find_one({"_id": id_clube})
            if registro is None:
                raise ValueError("O clube informado não existe.")
            clube = Clube(registro["_id"], registro["nome"], registro["cidade"])
            colecao = banco["JOGADORES"]
            jogador = Jogador(proximo_id(colecao), nome, posicao, clube)
            documento = {
                "_id": jogador.get_id_jogador(),
                "nome": jogador.get_nome(),
                "posicao": jogador.get_posicao(),
                "id_clube": jogador.get_id_clube(),
            }
            try:
                resultado = colecao.insert_one(documento)
            except DuplicateKeyError:
                raise ValueError("O ID do jogador já foi cadastrado. Tente novamente.") from None
            return resultado.inserted_id
        finally:
            conexao.close()
