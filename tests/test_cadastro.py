import unittest
from unittest.mock import MagicMock, patch

from pymongo.errors import DuplicateKeyError, OperationFailure
from pymongo.results import InsertOneResult

from src.controller.clube_controller import ClubeController
from src.controller.jogador_controller import JogadorController, POSICOES
from src.controller.validacoes import LIMITE_INTEIRO, proximo_id
from src.migracao import validar_base


class TestCadastro(unittest.TestCase):
    def setUp(self):
        self.conexao = MagicMock()
        for modulo in ("clube_controller", "jogador_controller"):
            fabrica = patch(f"src.controller.{modulo}.MongoQueries", return_value=self.conexao)
            fabrica.start()
            self.addCleanup(fabrica.stop)
        self.banco = self.conexao.connect.return_value
        self.banco.list_collection_names.return_value = ["CLUBES", "JOGADORES", "PARTIDAS", "GOLS"]
        self.clubes = MagicMock()
        self.jogadores = MagicMock()
        self.banco.__getitem__.side_effect = {"CLUBES": self.clubes, "JOGADORES": self.jogadores}.__getitem__
        self.clubes.find_one.return_value = None
        self.jogadores.find_one.return_value = None
        self.clubes.insert_one.side_effect = lambda doc: InsertOneResult(doc["_id"], True)
        self.jogadores.insert_one.side_effect = lambda doc: InsertOneResult(doc["_id"], True)
        self.registro_clube = {"_id": 12, "nome": "Clube A", "cidade": None}

    def test_clube_em_colecao_vazia_com_cidade_opcional(self):
        identificador = ClubeController().cadastrar_clube("  Clube A  ", "  ")
        self.assertEqual(identificador, 1)
        self.clubes.insert_one.assert_called_once_with({"_id": 1, "nome": "Clube A", "cidade": None})
        self.clubes.create_index.assert_called_once_with("nome", unique=True)
        self.conexao.close.assert_called_once()

    def test_clube_apos_ids_migrados_e_limites_de_texto(self):
        self.clubes.find_one.side_effect = [None, {"_id": 500}]
        identificador = ClubeController().cadastrar_clube("A" * 100, "B" * 80)
        self.assertEqual(identificador, 501)
        self.assertEqual(self.clubes.insert_one.call_args.args[0],
                         {"_id": 501, "nome": "A" * 100, "cidade": "B" * 80})
        self.assertEqual(self.clubes.find_one.call_args.kwargs["sort"], [("_id", -1)])

    def test_nomes_invalidos_nao_abrem_conexao(self):
        for nome in (None, "", "  ", "A" * 101, 123, True, {"$ne": ""}):
            for controlador in ("clube", "jogador"):
                with self.subTest(nome=nome, controlador=controlador):
                    with self.assertRaises(ValueError):
                        if controlador == "clube":
                            ClubeController().cadastrar_clube(nome)
                        else:
                            JogadorController().cadastrar_jogador(nome, "Atacante", 12)
        self.conexao.connect.assert_not_called()

    def test_cidades_invalidas_nao_abrem_conexao(self):
        for cidade in ("A" * 81, 123, False, []):
            with self.subTest(cidade=cidade):
                with self.assertRaises(ValueError):
                    ClubeController().cadastrar_clube("Clube A", cidade)
        self.conexao.connect.assert_not_called()

    def test_nome_de_clube_duplicado_nao_insere(self):
        self.clubes.find_one.return_value = self.registro_clube
        with self.assertRaisesRegex(ValueError, "Já existe"):
            ClubeController().cadastrar_clube("Clube A")
        self.clubes.insert_one.assert_not_called()
        self.conexao.close.assert_called_once()

    def test_duplicidades_antigas_impedem_criacao_do_indice(self):
        self.clubes.create_index.side_effect = DuplicateKeyError("duplicado")
        with self.assertRaisesRegex(ValueError, "duplicados na base"):
            ClubeController().cadastrar_clube("Novo clube")
        self.clubes.insert_one.assert_not_called()
        self.conexao.close.assert_called_once()

    def test_colisao_de_chave_no_clube_nao_sobrescreve(self):
        self.clubes.insert_one.side_effect = DuplicateKeyError("colisão")
        with self.assertRaisesRegex(ValueError, "ID ou nome"):
            ClubeController().cadastrar_clube("Clube A")
        self.assertNotIn("update_one", [c[0] for c in self.clubes.mock_calls])
        self.assertNotIn("replace_one", [c[0] for c in self.clubes.mock_calls])
        self.conexao.close.assert_called_once()

    def test_jogador_preserva_referencia_numerica_e_contrato_da_migracao(self):
        self.clubes.find_one.return_value = self.registro_clube
        identificador = JogadorController().cadastrar_jogador(" João ", " Atacante ", 12)
        documento = self.jogadores.insert_one.call_args.args[0]
        self.assertEqual(identificador, 1)
        self.assertEqual(documento, {"_id": 1, "nome": "João", "posicao": "Atacante", "id_clube": 12})
        validar_base({"CLUBES": [self.registro_clube], "JOGADORES": [documento], "PARTIDAS": [], "GOLS": []})
        self.clubes.find_one.assert_called_once_with({"_id": 12})
        self.conexao.close.assert_called_once()

    def test_jogador_apos_id_migrado(self):
        self.clubes.find_one.return_value = self.registro_clube
        self.jogadores.find_one.return_value = {"_id": 900}
        self.assertEqual(JogadorController().cadastrar_jogador("A" * 100, "Goleiro", 12), 901)

    def test_todas_as_posicoes_permitidas(self):
        self.clubes.find_one.return_value = self.registro_clube
        for posicao in POSICOES:
            with self.subTest(posicao=posicao):
                JogadorController().cadastrar_jogador("João", posicao, 12)
                self.assertEqual(self.jogadores.insert_one.call_args.args[0]["posicao"], posicao)

    def test_posicoes_invalidas_nao_abrem_conexao(self):
        for posicao in (None, "", "atacante", "Técnico", 1, "A" * 21):
            with self.subTest(posicao=posicao):
                with self.assertRaises(ValueError):
                    JogadorController().cadastrar_jogador("João", posicao, 12)
        self.conexao.connect.assert_not_called()

    def test_ids_de_clube_invalidos_nao_abrem_conexao(self):
        for identificador in (0, -1, True, False, 1.0, 1.5, "12", None, LIMITE_INTEIRO + 1):
            with self.subTest(identificador=identificador):
                with self.assertRaises(ValueError):
                    JogadorController().cadastrar_jogador("João", "Atacante", identificador)
        self.conexao.connect.assert_not_called()

    def test_clube_inexistente_nao_insere_jogador(self):
        with self.assertRaisesRegex(ValueError, "clube informado não existe"):
            JogadorController().cadastrar_jogador("João", "Atacante", 12)
        self.jogadores.insert_one.assert_not_called()
        self.conexao.close.assert_called_once()

    def test_jogadores_com_mesmo_nome_sao_permitidos(self):
        self.clubes.find_one.return_value = self.registro_clube
        self.jogadores.find_one.side_effect = [None, {"_id": 1}]
        primeiro = JogadorController().cadastrar_jogador("João", "Atacante", 12)
        segundo = JogadorController().cadastrar_jogador("João", "Atacante", 12)
        self.assertEqual((primeiro, segundo), (1, 2))
        self.jogadores.create_index.assert_not_called()

    def test_colisao_de_id_no_jogador_fecha_conexao(self):
        self.clubes.find_one.return_value = self.registro_clube
        self.jogadores.insert_one.side_effect = DuplicateKeyError("colisão")
        with self.assertRaisesRegex(ValueError, "ID do jogador"):
            JogadorController().cadastrar_jogador("João", "Atacante", 12)
        self.conexao.close.assert_called_once()

    def test_limite_de_id_impede_insercao(self):
        self.clubes.find_one.side_effect = [None, {"_id": LIMITE_INTEIRO}]
        with self.assertRaisesRegex(ValueError, "limite de identificadores"):
            ClubeController().cadastrar_clube("Clube A")
        self.clubes.insert_one.assert_not_called()
        self.conexao.close.assert_called_once()

    def test_ultimo_id_disponivel_e_id_existente_invalido(self):
        self.jogadores.find_one.return_value = {"_id": LIMITE_INTEIRO - 1}
        self.assertEqual(proximo_id(self.jogadores), LIMITE_INTEIRO)
        for identificador in (True, "1", 1.5, 0, -1, LIMITE_INTEIRO + 1):
            with self.subTest(identificador=identificador):
                self.jogadores.find_one.return_value = {"_id": identificador}
                with self.assertRaises(ValueError):
                    proximo_id(self.jogadores)

    def test_colecoes_ausentes_nao_sao_criadas_pelo_cadastro(self):
        self.banco.list_collection_names.return_value = []
        for cadastrar, argumentos in (
            (ClubeController().cadastrar_clube, ("Clube A",)),
            (JogadorController().cadastrar_jogador, ("João", "Atacante", 12)),
        ):
            with self.subTest(cadastrar=cadastrar.__name__):
                with self.assertRaisesRegex(ValueError, "criar_colecoes"):
                    cadastrar(*argumentos)
        self.banco.create_collection.assert_not_called()
        self.clubes.insert_one.assert_not_called()
        self.jogadores.insert_one.assert_not_called()

    def test_falha_de_conexao_fecha_cliente(self):
        self.conexao.connect.side_effect = ConnectionError("indisponível")
        with self.assertRaises(ConnectionError):
            ClubeController().cadastrar_clube("Clube A")
        self.conexao.close.assert_called_once()

    def test_falha_de_permissao_no_indice_nao_insere(self):
        self.clubes.create_index.side_effect = OperationFailure("Sem permissão")
        with self.assertRaises(OperationFailure):
            ClubeController().cadastrar_clube("Clube A")
        self.clubes.insert_one.assert_not_called()
        self.conexao.close.assert_called_once()

    def test_falha_de_escrita_fecha_conexao_do_jogador(self):
        self.clubes.find_one.return_value = self.registro_clube
        self.jogadores.insert_one.side_effect = OperationFailure("Falha de escrita")
        with self.assertRaises(OperationFailure):
            JogadorController().cadastrar_jogador("João", "Atacante", 12)
        self.conexao.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
