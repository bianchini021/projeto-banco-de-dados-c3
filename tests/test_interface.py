"""Casos cobertos:
- CT01: SplashScreen conta documentos nas 4 coleções (CLUBES, JOGADORES, PARTIDAS, GOLS)
        e exibe nome do projeto, integrantes, professor e quantidades.
- CT02: SplashScreen retorna False e exibe mensagem amigável quando o MongoDB falha.
- CT03: Constantes de menu contêm todas as opções obrigatórias do edital.
- CT04: Menu de relatórios aciona os 3 relatórios do MongoDB e encerra na opção 0.
- CT05: Menu de inserção cadastra clube e respeita a confirmação de continuar (s/n).
- CT06: main() interrompe a execução se a splash screen falhar e encerra na opção 0.
"""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from src import main as app_main
from src.utils import config, menus
from src.utils.splash_screen import SplashScreen

class TestSplashScreen(unittest.TestCase):
    @patch("src.utils.splash_screen.MongoQueries")
    def test_ct01_exibir_splash_com_contagens(self, mock_mongo_cls):
        """CT01: Exibe cabeçalho, integrantes e contagens iniciais de cada coleção."""
        contagens = {"CLUBES": 4, "JOGADORES": 20, "PARTIDAS": 6, "GOLS": 15}
        mock_banco = MagicMock()
        mock_banco.__getitem__.side_effect = lambda nome: MagicMock(
            count_documents=MagicMock(return_value=contagens[nome])
        )
        mock_instancia = mock_mongo_cls.return_value
        mock_instancia.connect.return_value = mock_banco

        saida = io.StringIO()
        with redirect_stdout(saida):
            ok = SplashScreen().exibir()

        texto = saida.getvalue()
        self.assertTrue(ok)
        self.assertIn("GERENCIADOR DE CAMPEONATO", texto)
        self.assertIn("Howard Roatti", texto)
        self.assertIn("2026/2", texto)
        self.assertIn("Vinicius Effgen de Oliveira", texto)
        self.assertIn("Clubes: 4", texto)
        self.assertIn("Jogadores: 20", texto)
        self.assertIn("Partidas: 6", texto)
        self.assertIn("Gols: 15", texto)
        mock_instancia.close.assert_called_once()

    @patch("src.utils.splash_screen.MongoQueries")
    def test_ct02_exibir_splash_erro_conexao(self, mock_mongo_cls):
        """CT02: Retorna False quando há falha de conexão com o MongoDB."""
        mock_instancia = mock_mongo_cls.return_value
        mock_instancia.connect.side_effect = ConnectionError("Servidor indisponível")

        saida = io.StringIO()
        with redirect_stdout(saida):
            ok = SplashScreen().exibir()

        texto = saida.getvalue()
        self.assertFalse(ok)
        self.assertIn("Não foi possível iniciar o sistema.", texto)
        mock_instancia.close.assert_called_once()

class TestConfigEMenus(unittest.TestCase):
    def test_ct03_opcoes_obrigatorias_nos_menus(self):
        """CT03: Verifica presença das opções exigidas pelo edital."""
        for trecho in ("Relatórios", "Inserir", "Atualizar", "Remover", "Sair"):
            self.assertIn(trecho, config.MENU_PRINCIPAL)
        for entidade in ("Clubes", "Jogadores", "Partidas", "Gols"):
            self.assertIn(entidade, config.MENU_ENTIDADES)

    @patch("src.utils.menus.Relatorio")
    @patch("src.utils.menus.MongoQueries")
    @patch("builtins.input", side_effect=["1", "2", "3", "9", "0"])
    def test_ct04_menu_relatorios_fluxo_completo(self, _mock_input, mock_mongo_cls, mock_rel_cls):
        """CT04: Executa os 3 relatórios, trata opção inválida e volta com 0."""
        saida = io.StringIO()
        with redirect_stdout(saida):
            menus.menu_relatorios()

        rel = mock_rel_cls.return_value
        rel.get_relatorio_artilharia.assert_called_once()
        rel.get_relatorio_partidas.assert_called_once()
        rel.get_relatorio_gols_detalhados.assert_called_once()
        self.assertEqual(mock_mongo_cls.return_value.close.call_count, 3)
        self.assertIn("Opção inválida.", saida.getvalue())

    @patch.object(menus.clubes, "cadastrar_clube", return_value=1)
    @patch("builtins.input", side_effect=["1", "Botafogo", "Rio de Janeiro", "n"])
    def test_ct05_menu_inserir_clube_e_encerrar_loop(self, _mock_input, mock_cadastrar):
        """CT05: Insere clube e retorna ao menu principal quando usuário responde 'n'."""
        saida = io.StringIO()
        with redirect_stdout(saida):
            menus.menu_operacao("inserir")

        mock_cadastrar.assert_called_once_with("Botafogo", "Rio de Janeiro")
        self.assertIn("Documento cadastrado com sucesso. ID: 1", saida.getvalue())

class TestMain(unittest.TestCase):
    @patch("src.main.splash_screen", return_value=False)
    def test_ct06_main_aborta_sem_splash(self, mock_splash):
        """CT06a: Não entra no loop principal se a splash screen falhar."""
        app_main.main()
        mock_splash.assert_called_once()

    @patch("src.main.splash_screen", return_value=True)
    @patch("builtins.input", side_effect=["9", "0"])
    def test_ct06_main_opcao_invalida_e_sair(self, _mock_input, _mock_splash):
        """CT06b: Trata opção inválida e encerra corretamente na opção 0."""
        saida = io.StringIO()
        with redirect_stdout(saida):
            app_main.main()

        texto = saida.getvalue()
        self.assertIn("Opção inválida.", texto)
        self.assertIn("Encerrando o programa...", texto)

if __name__ == "__main__":
    unittest.main()