import copy
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from pymongo.errors import CollectionInvalid, OperationFailure

from src.criar_colecoes import COLECOES, criar_colecoes, main


class TestCriarColecoes(unittest.TestCase):
    def setUp(self):
        fabrica = patch("src.criar_colecoes.MongoQueries")
        self.conexao = fabrica.start().return_value
        self.addCleanup(fabrica.stop)
        self.banco = self.conexao.connect.return_value
        self.colecoes = {}
        self.banco.list_collection_names.side_effect = lambda: list(self.colecoes)
        self.banco.create_collection.side_effect = self.criar_colecao

    def criar_colecao(self, nome):
        if nome in self.colecoes:
            raise CollectionInvalid("Coleção já existe")
        self.colecoes[nome] = []

    def test_cria_exatamente_as_quatro_colecoes(self):
        resultado = criar_colecoes()
        self.assertEqual(list(self.colecoes), ["CLUBES", "JOGADORES", "PARTIDAS", "GOLS"])
        self.assertTrue(all(documentos == [] for documentos in self.colecoes.values()))
        self.assertEqual(resultado, dict.fromkeys(COLECOES, "criada"))
        self.conexao.close.assert_called_once()

    def test_segunda_execucao_preserva_documentos_e_nao_recria(self):
        criar_colecoes()
        self.colecoes["CLUBES"].append({"_id": 7, "nome": "Clube A", "cidade": None})
        anterior = copy.deepcopy(self.colecoes)
        self.banco.reset_mock()
        resultado = criar_colecoes()
        self.assertEqual(self.colecoes, anterior)
        self.banco.create_collection.assert_not_called()
        self.assertEqual(resultado, dict.fromkeys(COLECOES, "já existente; preservada"))
        self.assertEqual([chamada[0] for chamada in self.banco.mock_calls],
                         ["list_collection_names"])

    def test_cria_apenas_ausentes_e_preserva_colecao_extra(self):
        self.colecoes.update({"CLUBES": [{"_id": 1}], "GOLS": [],
                             "OUTRA": [{"dado": "preservar"}]})
        anterior = copy.deepcopy(self.colecoes)
        criar_colecoes()
        self.assertEqual([c.args[0] for c in self.banco.create_collection.call_args_list],
                         ["JOGADORES", "PARTIDAS"])
        for nome, documentos in anterior.items():
            self.assertEqual(self.colecoes[nome], documentos)
        self.assertEqual([c[0] for c in self.banco.mock_calls],
                         ["list_collection_names", "create_collection", "create_collection"])

    def test_falha_parcial_permite_retomar(self):
        def falhar_em_partidas(nome):
            if nome == "PARTIDAS":
                raise OperationFailure("Sem permissão")
            self.criar_colecao(nome)

        self.banco.create_collection.side_effect = falhar_em_partidas
        with self.assertRaises(OperationFailure):
            criar_colecoes()
        self.assertEqual(list(self.colecoes), ["CLUBES", "JOGADORES"])
        self.conexao.close.assert_called_once()
        self.banco.create_collection.side_effect = self.criar_colecao
        criar_colecoes()
        self.assertEqual(list(self.colecoes), list(COLECOES))

    def test_falha_na_conexao_fecha_cliente(self):
        self.conexao.connect.side_effect = ConnectionError("Servidor indisponível")
        with self.assertRaises(ConnectionError):
            criar_colecoes()
        self.conexao.close.assert_called_once()
        self.banco.create_collection.assert_not_called()

    def test_falha_na_listagem_nao_cria_colecoes(self):
        self.banco.list_collection_names.side_effect = OperationFailure("Sem permissão")
        with self.assertRaises(OperationFailure):
            criar_colecoes()
        self.conexao.close.assert_called_once()
        self.banco.create_collection.assert_not_called()

    def test_main_informa_sucesso(self):
        saida = io.StringIO()
        with redirect_stdout(saida):
            codigo = main()
        self.assertEqual(codigo, 0)
        for nome in COLECOES:
            self.assertIn(f"{nome}: criada.", saida.getvalue())

    def test_main_informa_falha_sem_expor_detalhes_da_conexao(self):
        self.conexao.connect.side_effect = ConnectionError("senha_secreta")
        saida = io.StringIO()
        with redirect_stdout(saida):
            codigo = main()
        self.assertEqual(codigo, 1)
        self.assertNotIn("senha_secreta", saida.getvalue())
        self.assertIn("execute o script novamente", saida.getvalue())


if __name__ == "__main__":
    unittest.main()
