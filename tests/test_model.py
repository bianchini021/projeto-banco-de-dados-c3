import unittest
from datetime import datetime, timezone

from src.model.clube import Clube
from src.model.gol import Gol
from src.model.jogador import Jogador
from src.model.partida import Partida


class TestModelos(unittest.TestCase):
    def setUp(self):
        self.mandante = Clube(1, "Clube A", None)
        self.visitante = Clube(2, "Clube B", "Vitória")
        self.jogador = Jogador(3, "João", "Atacante", self.mandante)
        self.partida = Partida(
            4, self.mandante, self.visitante, 1,
            datetime(2026, 11, 24, tzinfo=timezone.utc),
        )

    def test_associacoes_preservam_objetos_e_identificadores(self):
        gol = Gol(5, self.partida, self.jogador, 47)
        self.assertIs(self.jogador.get_clube(), self.mandante)
        self.assertIs(self.partida.get_mandante(), self.mandante)
        self.assertIs(self.partida.get_visitante(), self.visitante)
        self.assertIs(gol.get_partida(), self.partida)
        self.assertIs(gol.get_jogador(), self.jogador)
        self.assertEqual(self.jogador.get_id_clube(), 1)
        self.assertEqual(self.partida.get_id_mandante(), 1)
        self.assertEqual(self.partida.get_id_visitante(), 2)
        self.assertEqual(gol.get_id_partida(), 4)
        self.assertEqual(gol.get_id_jogador(), 3)

    def test_associacoes_nao_aceitam_ids_no_lugar_de_objetos(self):
        setters = (
            self.jogador.set_clube,
            self.partida.set_mandante,
            self.partida.set_visitante,
            Gol().set_partida,
            Gol().set_jogador,
        )
        for setter in setters:
            with self.subTest(setter=setter.__name__):
                with self.assertRaises(TypeError):
                    setter(1)

    def test_partida_nova_aberta_com_placar_nulo(self):
        self.assertEqual(self.partida.get_status(), "ABERTA")
        self.assertIsNone(self.partida.get_gols_mandante())
        self.assertIsNone(self.partida.get_gols_visitante())
        self.assertIn("Clube A - x - Clube B", self.partida.to_string())

    def test_exibicao_da_data_preserva_dia_utc_sem_horario(self):
        texto = self.partida.to_string()
        self.assertIn("Data: 2026-11-24 |", texto)
        self.assertNotIn("00:00", texto)
        self.assertEqual(self.partida.get_data_partida(),
                         datetime(2026, 11, 24, tzinfo=timezone.utc))

    def test_representa_partida_finalizada_existente_com_empate_sem_gols(self):
        partida = Partida(6, self.mandante, self.visitante, 2,
                          datetime(2026, 11, 25, tzinfo=timezone.utc),
                          "FINALIZADA", 0, 0)
        self.assertIn("Clube A 0 x 0 Clube B", partida.to_string())
        self.assertIn("Status: FINALIZADA", partida.to_string())

    def test_gols_distintos_no_mesmo_minuto(self):
        primeiro = Gol(5, self.partida, self.jogador, 47)
        segundo = Gol(6, self.partida, self.jogador, 47)
        self.assertNotEqual(primeiro.get_id_gol(), segundo.get_id_gol())
        self.assertEqual(primeiro.get_minuto(), segundo.get_minuto())
        self.assertIn("Jogador: João", primeiro.to_string())
        self.assertIn("Clube: Clube A", self.jogador.to_string())

    def test_clube_sem_cidade_e_objetos_ainda_nao_preenchidos(self):
        self.assertIsNone(self.mandante.get_cidade())
        for modelo in (Clube(), Jogador(), Partida(), Gol()):
            with self.subTest(modelo=type(modelo).__name__):
                self.assertIsInstance(modelo.to_string(), str)
        self.assertIsNone(Jogador().get_id_clube())
        self.assertIsNone(Gol().get_id_partida())


if __name__ == "__main__":
    unittest.main()