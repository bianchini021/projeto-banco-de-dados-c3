import copy
import unittest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from bson import BSON
from pymongo.errors import DuplicateKeyError, OperationFailure
from pymongo.results import InsertOneResult

from src.controller.gol_controller import GolController
from src.controller.partida_controller import PartidaController, validar_data
from src.controller.validacoes import LIMITE_INTEIRO
from src.migracao import validar_base


class TestPartidasGols(unittest.TestCase):
    def setUp(self):
        self.conexao = MagicMock()
        for modulo in ("partida_controller", "gol_controller"):
            fabrica = patch(f"src.controller.{modulo}.MongoQueries", return_value=self.conexao)
            fabrica.start()
            self.addCleanup(fabrica.stop)
        self.banco = self.conexao.connect.return_value
        self.colecoes = {nome: MagicMock() for nome in ("CLUBES", "JOGADORES", "PARTIDAS", "GOLS")}
        self.banco.__getitem__.side_effect = self.colecoes.__getitem__
        self.banco.list_collection_names.return_value = list(self.colecoes)
        self.clubes = {1: {"_id": 1, "nome": "A", "cidade": None},
                       2: {"_id": 2, "nome": "B", "cidade": None}}
        self.partida = {"_id": 10, "id_mandante": 1, "id_visitante": 2, "rodada": 1,
                        "data_partida": datetime(2026, 11, 24, tzinfo=timezone.utc),
                        "status": "ABERTA", "gols_mandante": None, "gols_visitante": None}
        self.jogador = {"_id": 20, "nome": "João", "posicao": "Atacante", "id_clube": 1}
        self.colecoes["CLUBES"].find_one.side_effect = lambda filtro: self.clubes.get(filtro["_id"])
        self.colecoes["JOGADORES"].find_one.return_value = self.jogador
        self.colecoes["PARTIDAS"].find_one.return_value = None
        self.colecoes["GOLS"].find_one.return_value = None
        for colecao in self.colecoes.values():
            colecao.insert_one.side_effect = lambda doc: InsertOneResult(doc["_id"], True)

    def preparar_gol(self):
        self.colecoes["PARTIDAS"].find_one.return_value = self.partida

    def test_partida_nova_respeita_contrato_e_bson(self):
        identificador = PartidaController().cadastrar_partida(1, 2, 1, "2026-11-24")
        doc = self.colecoes["PARTIDAS"].insert_one.call_args.args[0]
        self.assertEqual(identificador, 1)
        self.assertEqual(doc, dict(self.partida, _id=1))
        validar_base({"CLUBES": list(self.clubes.values()), "JOGADORES": [], "PARTIDAS": [doc], "GOLS": []})
        decodificado = BSON(BSON.encode(doc)).decode()
        self.assertEqual(decodificado["data_partida"], datetime(2026, 11, 24))
        self.conexao.close.assert_called_once()

    def test_datas_validas_e_ano_bissexto(self):
        for valor in ("2024-02-29", " 2024-02-29 ", date(2024, 2, 29)):
            with self.subTest(valor=valor):
                self.assertEqual(validar_data(valor), datetime(2024, 2, 29, tzinfo=timezone.utc))

    def test_datas_invalidas_nao_abrem_conexao(self):
        for valor in (None, True, 20261124, "", "2026-02-29", "2026-13-01", "24/11/2026",
                      "20261124", "2026-W48-2", "2026-11-24T00:00:00", datetime(2026, 11, 24)):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    PartidaController().cadastrar_partida(1, 2, 1, valor)
        self.conexao.connect.assert_not_called()

    def test_inteiros_invalidos_na_partida(self):
        for campo in range(3):
            for valor in (0, -1, True, "1", 1.0, None, LIMITE_INTEIRO + 1):
                argumentos = [1, 2, 1, "2026-11-24"]
                argumentos[campo] = valor
                with self.subTest(campo=campo, valor=valor):
                    with self.assertRaises(ValueError):
                        PartidaController().cadastrar_partida(*argumentos)
        self.conexao.connect.assert_not_called()

    def test_clubes_iguais(self):
        with self.assertRaisesRegex(ValueError, "diferentes"):
            PartidaController().cadastrar_partida(1, 1, 1, "2026-11-24")
        self.conexao.connect.assert_not_called()

    def test_clubes_inexistentes(self):
        for mandante, visitante in ((3, 2), (1, 3)):
            with self.subTest(mandante=mandante, visitante=visitante):
                with self.assertRaisesRegex(ValueError, "cadastrados"):
                    PartidaController().cadastrar_partida(mandante, visitante, 1, "2026-11-24")
        self.colecoes["PARTIDAS"].insert_one.assert_not_called()
        self.assertEqual(self.conexao.close.call_count, 2)

    def test_confronto_repetido_direto_e_invertido(self):
        def buscar(filtro):
            self.assertEqual(filtro["rodada"], 1)
            return self.partida if any(all(self.partida[k] == v for k, v in alternativa.items())
                                      for alternativa in filtro["$or"]) else None
        self.colecoes["PARTIDAS"].find_one.side_effect = buscar
        for mandante, visitante in ((1, 2), (2, 1)):
            with self.subTest(mandante=mandante):
                with self.assertRaisesRegex(ValueError, "nesta rodada"):
                    PartidaController().cadastrar_partida(mandante, visitante, 1, "2026-12-01")
        self.colecoes["PARTIDAS"].insert_one.assert_not_called()

    def test_mesmo_confronto_em_outra_rodada_e_id_migrado(self):
        def buscar(filtro, *args, **kwargs):
            if "sort" in kwargs:
                return {"_id": 800}
            return self.partida if filtro["rodada"] == 1 else None
        self.colecoes["PARTIDAS"].find_one.side_effect = buscar
        self.assertEqual(PartidaController().cadastrar_partida(2, 1, 2, "2026-12-01"), 801)

    def test_gol_dos_dois_clubes_sem_alterar_placar(self):
        self.preparar_gol()
        antes = copy.deepcopy(self.partida)
        for clube, minuto in ((1, 1), (2, 130)):
            with self.subTest(clube=clube):
                self.jogador["id_clube"] = clube
                self.assertEqual(GolController().cadastrar_gol(10, 20, minuto), 1)
                doc = self.colecoes["GOLS"].insert_one.call_args.args[0]
                self.assertEqual(doc, {"_id": 1, "id_partida": 10, "id_jogador": 20, "minuto": minuto})
                validar_base({"CLUBES": list(self.clubes.values()), "JOGADORES": [self.jogador],
                              "PARTIDAS": [self.partida], "GOLS": [doc]})
                self.assertEqual(BSON(BSON.encode(doc)).decode(), doc)
        self.assertEqual(self.partida, antes)
        self.colecoes["PARTIDAS"].update_one.assert_not_called()
        self.colecoes["PARTIDAS"].replace_one.assert_not_called()

    def test_gols_no_mesmo_minuto_sao_permitidos(self):
        self.preparar_gol()
        self.colecoes["GOLS"].find_one.side_effect = [{"_id": 90}, {"_id": 91}]
        primeiro = GolController().cadastrar_gol(10, 20, 47)
        segundo = GolController().cadastrar_gol(10, 20, 47)
        self.assertEqual((primeiro, segundo), (91, 92))
        self.colecoes["GOLS"].create_index.assert_not_called()

    def test_ids_e_minutos_invalidos(self):
        for campo in range(3):
            valores = [0, -1, True, False, "1", 1.0, None, LIMITE_INTEIRO + 1]
            if campo == 2:
                valores += [131, "45+2"]
            for valor in valores:
                args = [10, 20, 47]
                args[campo] = valor
                with self.subTest(campo=campo, valor=valor):
                    with self.assertRaises(ValueError):
                        GolController().cadastrar_gol(*args)
        self.conexao.connect.assert_not_called()

    def test_partida_inexistente(self):
        with self.assertRaisesRegex(ValueError, "partida informada não existe"):
            GolController().cadastrar_gol(10, 20, 47)
        self.colecoes["GOLS"].insert_one.assert_not_called()
        self.conexao.close.assert_called_once()

    def test_jogador_inexistente(self):
        self.preparar_gol()
        self.colecoes["JOGADORES"].find_one.return_value = None
        with self.assertRaisesRegex(ValueError, "jogador informado não existe"):
            GolController().cadastrar_gol(10, 20, 47)
        self.colecoes["GOLS"].insert_one.assert_not_called()

    def test_partida_finalizada_ou_estado_invalido(self):
        self.preparar_gol()
        for status in ("FINALIZADA", "CANCELADA", None):
            with self.subTest(status=status):
                self.partida["status"] = status
                with self.assertRaisesRegex(ValueError, "ABERTAS"):
                    GolController().cadastrar_gol(10, 20, 47)
        self.colecoes["GOLS"].insert_one.assert_not_called()

    def test_jogador_de_clube_fora_da_partida(self):
        self.preparar_gol()
        self.jogador["id_clube"] = 3
        with self.assertRaisesRegex(ValueError, "não pertence"):
            GolController().cadastrar_gol(10, 20, 47)
        self.colecoes["GOLS"].insert_one.assert_not_called()

    def test_partida_com_clube_ausente_ou_igual(self):
        self.preparar_gol()
        del self.clubes[2]
        with self.assertRaisesRegex(ValueError, "clubes da partida não existe"):
            GolController().cadastrar_gol(10, 20, 47)
        self.partida["id_visitante"] = 1
        with self.assertRaisesRegex(ValueError, "clubes iguais"):
            GolController().cadastrar_gol(10, 20, 47)
        self.colecoes["GOLS"].insert_one.assert_not_called()

    def test_partida_aberta_com_placar_inconsistente(self):
        self.preparar_gol()
        self.partida["gols_mandante"] = 0
        with self.assertRaisesRegex(ValueError, "placar inconsistente"):
            GolController().cadastrar_gol(10, 20, 47)
        self.colecoes["GOLS"].insert_one.assert_not_called()

    def test_colisoes_e_falhas_de_escrita_fecham_conexao(self):
        for nome, metodo, args in (
            ("PARTIDAS", PartidaController().cadastrar_partida, (1, 2, 1, "2026-11-24")),
            ("GOLS", GolController().cadastrar_gol, (10, 20, 47)),
        ):
            if nome == "GOLS":
                self.preparar_gol()
            for erro, tipo in ((DuplicateKeyError("duplicado"), ValueError),
                               (OperationFailure("falha"), OperationFailure)):
                with self.subTest(colecao=nome, erro=tipo.__name__):
                    self.conexao.close.reset_mock()
                    self.colecoes[nome].insert_one.side_effect = erro
                    with self.assertRaises(tipo):
                        metodo(*args)
                    self.conexao.close.assert_called_once()
                    self.colecoes[nome].update_one.assert_not_called()

    def test_limite_de_identificadores(self):
        self.colecoes["PARTIDAS"].find_one.side_effect = [None, {"_id": LIMITE_INTEIRO}]
        with self.assertRaisesRegex(ValueError, "limite de identificadores"):
            PartidaController().cadastrar_partida(1, 2, 1, "2026-11-24")
        self.colecoes["PARTIDAS"].find_one.side_effect = None
        self.preparar_gol()
        self.colecoes["GOLS"].find_one.return_value = {"_id": LIMITE_INTEIRO}
        with self.assertRaisesRegex(ValueError, "limite de identificadores"):
            GolController().cadastrar_gol(10, 20, 47)
        self.colecoes["PARTIDAS"].insert_one.assert_not_called()
        self.colecoes["GOLS"].insert_one.assert_not_called()

    def test_colecoes_ausentes_e_falha_de_conexao(self):
        for metodo, args in (
            (PartidaController().cadastrar_partida, (1, 2, 1, "2026-11-24")),
            (GolController().cadastrar_gol, (10, 20, 47)),
        ):
            with self.subTest(metodo=metodo.__name__):
                self.banco.list_collection_names.return_value = []
                with self.assertRaisesRegex(ValueError, "criar_colecoes"):
                    metodo(*args)
                self.conexao.connect.side_effect = ConnectionError("indisponível")
                with self.assertRaises(ConnectionError):
                    metodo(*args)
                self.conexao.connect.side_effect = None
        self.assertEqual(self.conexao.close.call_count, 4)
        self.colecoes["PARTIDAS"].insert_one.assert_not_called()
        self.colecoes["GOLS"].insert_one.assert_not_called()


if __name__ == "__main__":
    unittest.main()
