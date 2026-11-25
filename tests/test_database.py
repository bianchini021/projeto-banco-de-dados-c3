import os
import unittest
from unittest.mock import patch

from pymongo.errors import InvalidURI, OperationFailure, ServerSelectionTimeoutError

from src.utils.database import MongoQueries


class TestMongoQueries(unittest.TestCase):
    def setUp(self):
        ambiente = patch.dict(os.environ, {"MONGO_DATABASE": "campeonato_teste"}, clear=True)
        ambiente.start()
        self.addCleanup(ambiente.stop)
        cliente = patch("src.utils.database.MongoClient")
        self.criar_cliente = cliente.start()
        self.addCleanup(cliente.stop)
        self.cliente = self.criar_cliente.return_value
        self.banco = self.cliente.__getitem__.return_value
        self.banco.write_concern.acknowledged = True
        self.conexao = MongoQueries()
        self.addCleanup(self.conexao.close)

    def test_conecta_com_configuracao_padrao(self):
        self.assertIs(self.conexao.connect(), self.banco)
        self.criar_cliente.assert_called_once_with(
            "mongodb://localhost:27017", serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000, socketTimeoutMS=30000, tz_aware=True,
        )
        self.cliente.__getitem__.assert_called_once_with("campeonato_teste")
        self.cliente.admin.command.assert_called_once_with("ping")

    def test_utiliza_uri_do_ambiente(self):
        os.environ["MONGO_URI"] = "mongodb://servidor:27018/?authSource=admin"
        self.conexao.connect()
        self.assertEqual(self.criar_cliente.call_args.args[0], os.environ["MONGO_URI"])

    def test_banco_obrigatorio(self):
        for valor in (None, "", "   "):
            with self.subTest(valor=valor):
                if valor is None:
                    os.environ.pop("MONGO_DATABASE", None)
                else:
                    os.environ["MONGO_DATABASE"] = valor
                with self.assertRaisesRegex(ValueError, "MONGO_DATABASE"):
                    self.conexao.connect()
        self.criar_cliente.assert_not_called()

    def test_uri_vazia(self):
        os.environ["MONGO_URI"] = "   "
        with self.assertRaisesRegex(ValueError, "MONGO_URI"):
            self.conexao.connect()
        self.criar_cliente.assert_not_called()

    def test_reutiliza_conexao_e_permite_reabrir(self):
        self.conexao.connect()
        self.assertIs(self.conexao.connect(), self.banco)
        self.criar_cliente.assert_called_once()
        self.conexao.close()
        self.conexao.connect()
        self.assertEqual(self.criar_cliente.call_count, 2)

    def test_fechamento_repetido_e_sem_conexao(self):
        self.conexao.close()
        self.cliente.close.assert_not_called()
        self.conexao.connect()
        self.conexao.close()
        self.conexao.close()
        self.cliente.close.assert_called_once()
        self.assertIsNone(self.conexao.mongo_client)
        self.assertIsNone(self.conexao.db)

    def test_falha_no_ping_fecha_cliente_e_nao_expoe_segredos(self):
        for erro in (ServerSelectionTimeoutError("senha_secreta"),
                     OperationFailure("senha_secreta", code=18)):
            with self.subTest(erro=type(erro).__name__):
                self.cliente.reset_mock()
                self.cliente.admin.command.side_effect = erro
                with self.assertRaises(ConnectionError) as resultado:
                    self.conexao.connect()
                self.assertNotIn("senha_secreta", str(resultado.exception))
                self.cliente.close.assert_called_once()
                self.assertIsNone(self.conexao.mongo_client)
                self.assertIsNone(self.conexao.db)
        self.cliente.admin.command.side_effect = None
        self.assertIs(self.conexao.connect(), self.banco)

    def test_uri_invalida(self):
        self.criar_cliente.side_effect = InvalidURI("senha_secreta")
        with self.assertRaises(ConnectionError) as resultado:
            self.conexao.connect()
        self.assertNotIn("senha_secreta", str(resultado.exception))
        self.assertIsNone(self.conexao.mongo_client)

    def test_rejeita_escritas_sem_confirmacao(self):
        self.banco.write_concern.acknowledged = False
        with self.assertRaisesRegex(ConnectionError, "w >= 1"):
            self.conexao.connect()
        self.cliente.close.assert_called_once()
        self.cliente.admin.command.assert_not_called()
        self.assertIsNone(self.conexao.db)

    def test_nome_de_banco_invalido_fecha_cliente(self):
        self.cliente.__getitem__.side_effect = ValueError("Nome inválido")
        with self.assertRaises(ConnectionError):
            self.conexao.connect()
        self.cliente.close.assert_called_once()
        self.assertIsNone(self.conexao.mongo_client)


if __name__ == "__main__":
    unittest.main()
