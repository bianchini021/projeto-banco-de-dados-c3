from pymongo.errors import PyMongoError

from src.controller.clube_controller import ClubeController
from src.controller.gol_controller import GolController
from src.controller.jogador_controller import JogadorController
from src.controller.partida_controller import PartidaController
from src.reports.relatorios import Relatorio
from src.utils.config import MENU_ENTIDADES, MENU_RELATORIOS
from src.utils.database import MongoQueries

clubes = ClubeController()
jogadores = JogadorController()
partidas = PartidaController()
gols = GolController()

def ler_inteiro(mensagem, atual=None):
    dica = f" [{atual}]" if atual is not None else ""
    while True:
        resposta = input(f"{mensagem}{dica}: ").strip()
        if not resposta:
            if atual is not None:
                return atual
            print("Campo obrigatório. Informe um número inteiro.")
            continue
        try:
            numero = int(resposta)
        except ValueError:
            print("Valor inválido. Digite um número inteiro (ex.: 1).")
            continue
        if numero < 1:
            print("Informe um número inteiro maior que zero.")
            continue
        return numero

def ler_texto(mensagem, atual=None):
    dica = f" [{atual}]" if atual is not None else ""
    resposta = input(f"{mensagem}{dica}: ").strip()
    return resposta if resposta else (atual if atual is not None else "")

def confirmar(mensagem):
    return input(f"{mensagem} (s/n): ").strip().lower() == "s"

def mostrar_registros(entidade):
    match entidade:
        case "1":
            registros = clubes.listar_clubes()
        case "2":
            registros = jogadores.listar_jogadores()
        case "3":
            registros = partidas.listar_partidas()
        case "4":
            registros = gols.listar_gols()
        case _:
            return []

    if not registros:
        print("Nenhum documento encontrado.")
    else:
        for registro in registros:
            print(registro.to_string() if hasattr(registro, "to_string") else registro)
    return registros

def buscar_registro(entidade, identificador):
    match entidade:
        case "1":
            return clubes.buscar_clube(identificador)
        case "2":
            return jogadores.buscar_jogador(identificador)
        case "3":
            return partidas.buscar_partida(identificador)
        case "4":
            return gols.buscar_gol(identificador)

def _tentar_listar(entidade):
    """Lista registros de apoio no cadastro sem falhar caso o método ainda não exista."""
    try:
        mostrar_registros(entidade)
    except AttributeError:
        pass

def informar_dados(entidade, atual=None):
    """Solicita os campos da entidade, mantendo dados anteriores na atualização."""
    match entidade:
        case "1":
            nome = ler_texto("Nome", atual.get_nome() if atual else None)
            cidade = ler_texto("Cidade (opcional)", atual.get_cidade() if atual else None)
            return nome, (cidade if cidade else None)
        case "2":
            print("Posições: Goleiro, Zagueiro, Lateral, Volante, Meio-Campo, Atacante")
            _tentar_listar("1")
            return (
                ler_texto("Nome", atual.get_nome() if atual else None),
                ler_texto("Posição", atual.get_posicao() if atual else None),
                ler_inteiro("ID do clube", atual.get_id_clube() if atual else None),
            )
        case "3":
            _tentar_listar("1")
            mandante = ler_inteiro("ID do mandante", atual.get_id_mandante() if atual else None)
            visitante = ler_inteiro("ID do visitante", atual.get_id_visitante() if atual else None)
            rodada = ler_inteiro("Rodada", atual.get_rodada() if atual else None)
            data = ler_texto("Data (AAAA-MM-DD)", str(atual.get_data_partida()) if atual else None)
            if atual is None:
                return mandante, visitante, rodada, data
            status = ler_texto("Status (ABERTA/FINALIZADA)", atual.get_status()).upper()
            if status == "FINALIZADA":
                print("O placar será calculado automaticamente pelos gols cadastrados.")
            return mandante, visitante, rodada, data, status
        case "4":
            _tentar_listar("3")
            _tentar_listar("2")
            return (
                ler_inteiro("ID da partida", atual.get_id_partida() if atual else None),
                ler_inteiro("ID do jogador", atual.get_id_jogador() if atual else None),
                ler_inteiro("Minuto", atual.get_minuto() if atual else None),
            )

def cadastrar(entidade):
    dados = informar_dados(entidade)
    match entidade:
        case "1":
            identificador = clubes.cadastrar_clube(*dados)
        case "2":
            identificador = jogadores.cadastrar_jogador(*dados)
        case "3":
            identificador = partidas.cadastrar_partida(*dados)
        case "4":
            identificador = gols.cadastrar_gol(*dados)
    print(f"Documento cadastrado com sucesso. ID: {identificador}")

def atualizar(entidade):
    if not mostrar_registros(entidade):
        return
    identificador = ler_inteiro("ID do documento para atualizar")
    atual = buscar_registro(entidade, identificador)
    if atual is None:
        print("Documento não encontrado.")
        return
    print("Atual:", atual.to_string())
    print("Pressione Enter para manter um valor já preenchido.")
    dados = informar_dados(entidade, atual)
    match entidade:
        case "1":
            alterou = clubes.atualizar_clube(identificador, *dados)
        case "2":
            alterou = jogadores.atualizar_jogador(identificador, *dados)
        case "3":
            alterou = partidas.atualizar_partida(identificador, *dados)
        case "4":
            alterou = gols.atualizar_gol(identificador, *dados)
    if alterou:
        atualizado = buscar_registro(entidade, identificador)
        print("Documento atualizado:", atualizado.to_string() if atualizado else identificador)
    else:
        print("O documento não foi encontrado para atualização.")

def remover(entidade):
    if not mostrar_registros(entidade):
        return
    identificador = ler_inteiro("ID do documento para remover")
    atual = buscar_registro(entidade, identificador)
    if atual is None:
        print("Documento não encontrado.")
        return
    print("Selecionado:", atual.to_string())
    if not confirmar("Confirma a exclusão deste documento?"):
        print("Exclusão cancelada. Retornando ao menu principal.")
        return "cancelado"
    match entidade:
        case "1":
            excluiu = clubes.excluir_clube(identificador)
        case "2":
            excluiu = jogadores.excluir_jogador(identificador)
        case "3":
            excluiu = partidas.excluir_partida(identificador)
        case "4":
            excluiu = gols.excluir_gol(identificador)
    print("Documento excluído." if excluiu else "Documento não encontrado.")
    return "excluido" if excluiu else "nao_encontrado"

def consultar(entidade):
    mostrar_registros(entidade)

def menu_operacao(acao):
    while True:
        print(MENU_ENTIDADES)
        entidade = input("Escolha uma entidade: ").strip()
        match entidade:
            case "0":
                return
            case "1" | "2" | "3" | "4":
                try:
                    match acao:
                        case "inserir":
                            cadastrar(entidade)
                        case "atualizar":
                            atualizar(entidade)
                        case "remover":
                            if remover(entidade) == "cancelado":
                                return
                        case "consultar":
                            consultar(entidade)
                except (ValueError, ConnectionError, PyMongoError) as erro:
                    print(f"Operação não realizada: {erro}")
                except (AttributeError, NotImplementedError):
                    print("Funcionalidade ainda não implementada no controller desta entidade.")
                pergunta = {
                    "inserir": "Deseja inserir mais algum documento?",
                    "atualizar": "Deseja atualizar mais algum documento?",
                    "remover": "Deseja excluir mais algum documento?",
                    "consultar": "Deseja consultar mais algum documento?",
                }[acao]
                if not confirmar(pergunta):
                    return
            case _:
                print("Opção inválida. Tente novamente.")

def menu_relatorios():
    while True:
        print(MENU_RELATORIOS)
        opcao = input("Escolha um relatório: ").strip()
        if opcao == "0":
            return
        if opcao not in ("1", "2", "3"):
            print("Opção inválida.")
            continue
        conexao = MongoQueries()
        try:
            banco = conexao.connect()
            relatorios = Relatorio(banco)
            match opcao:
                case "1":
                    relatorios.get_relatorio_artilharia()
                case "2":
                    relatorios.get_relatorio_partidas()
                case "3":
                    relatorios.get_relatorio_gols_detalhados()
        except (ConnectionError, PyMongoError, OSError) as erro:
            print(f"Não foi possível gerar o relatório: {erro}")
        finally:
            conexao.close()