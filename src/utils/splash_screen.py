from src.utils.database import MongoQueries

class SplashScreen:
    def __init__(self):
        self.projeto = "GERENCIADOR DE CAMPEONATO"
        self.professor = "Howard Roatti"
        self.disciplina = "Banco de Dados"
        self.semestre = "2026/2"
        self.turma = "4SC1"
        self.integrantes = [
            "Betania Almeida Lopes",
            "Eduardo Bianchini Borges",
            "Gabriel Santos Assis",
            "Vinicius Effgen de Oliveira",
            "Vitor de Oliveira Soares",
        ]
        self.colecoes = ("CLUBES", "JOGADORES", "PARTIDAS", "GOLS")

    def contar_registros(self):
        conexao = MongoQueries()
        try:
            banco = conexao.connect()
            quantidades = {}
            for colecao in self.colecoes:
                quantidades[colecao] = banco[colecao].count_documents({})
            return quantidades
        finally:
            conexao.close()

    def exibir(self):
        print("\n" + "=" * 46)
        print(self.projeto.center(46))
        print("=" * 46)
        print(f"Professor: {self.professor}")
        print(f"Disciplina: {self.disciplina}")
        print(f"Semestre: {self.semestre}")
        print(f"Turma: {self.turma}")
        print("Integrantes:")
        for nome in self.integrantes:
            print(f"  - {nome}")

        print("-" * 46)
        print("DOCUMENTOS CADASTRADOS")
        try:
            quantidades = self.contar_registros()
        except Exception as erro:
            print("Não foi possível consultar o banco de dados.")
            print(f"Detalhes: {erro}")
            print("-" * 46)
            print("Não foi possível iniciar o sistema.")
            print("Verifique a conexão com o MongoDB (MONGO_URI,")
            print("MONGO_DATABASE) e a criação das coleções.")
            print("=" * 46)
            return False
        else:
            for colecao, quantidade in quantidades.items():
                print(f"{colecao.capitalize()}: {quantidade}")
        print("=" * 46)
        return True


def splash_screen():
    return SplashScreen().exibir()