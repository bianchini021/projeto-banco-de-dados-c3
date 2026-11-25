from pymongo.errors import PyMongoError

from src.utils.database import MongoQueries


COLECOES = ("CLUBES", "JOGADORES", "PARTIDAS", "GOLS")


def criar_colecoes():
    conexao = MongoQueries()
    try:
        banco = conexao.connect()
        existentes = set(banco.list_collection_names())
        resultado = {}
        for nome in COLECOES:
            if nome in existentes:
                resultado[nome] = "já existente; preservada"
            else:
                banco.create_collection(nome)
                resultado[nome] = "criada"
        return resultado
    finally:
        conexao.close()


def main():
    try:
        resultado = criar_colecoes()
    except (ConnectionError, ValueError, PyMongoError):
        print("Não foi possível concluir a criação das coleções. "
              "Confira a conexão e as permissões no MongoDB.")
        print("As coleções já existentes ou criadas foram preservadas. "
              "Após corrigir a causa, execute o script novamente.")
        return 1

    for nome, situacao in resultado.items():
        print(f"{nome}: {situacao}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
