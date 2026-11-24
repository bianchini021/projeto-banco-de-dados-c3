import argparse
import getpass
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal


TABELAS = {
    "CLUBES": ("id_clube", "nome", "cidade"),
    "JOGADORES": ("id_jogador", "nome", "posicao", "id_clube"),
    "PARTIDAS": (
        "id_partida", "id_mandante", "id_visitante", "rodada", "data_partida",
        "status", "gols_mandante", "gols_visitante",
    ),
    "GOLS": ("id_gol", "id_partida", "id_jogador", "minuto"),
}


def converter_valor(campo, valor):
    if campo.startswith("id_") or campo in {"rodada", "minuto", "gols_mandante", "gols_visitante"}:
        if valor is None and campo.startswith("gols_"):
            return None
        if isinstance(valor, bool) or not isinstance(valor, (int, float, Decimal)):
            raise ValueError(f"{campo}: esperado um inteiro.")
        if isinstance(valor, float) and (not valor.is_integer() or abs(valor) >= 2**53):
            raise ValueError(f"{campo}: numero com precisao insegura.")
        if isinstance(valor, Decimal) and (not valor.is_finite() or valor != valor.to_integral_value()):
            raise ValueError(f"{campo}: esperado um inteiro.")
        minimo = 0 if campo.startswith("gols_") else 1
        maximo = 130 if campo == "minuto" else 2**63 - 1
        if not minimo <= valor <= maximo:
            raise ValueError(f"{campo}: valor fora do intervalo permitido.")
        return int(valor)
    if campo == "data_partida":
        if not isinstance(valor, date):
            raise ValueError("data_partida: esperado DATE do Oracle.")
        if isinstance(valor, datetime):
            if any((valor.hour, valor.minute, valor.second, valor.microsecond)) or valor.utcoffset() is not None:
                raise ValueError("data_partida: esperado DATE sem horario ou fuso.")
        return datetime(valor.year, valor.month, valor.day, tzinfo=timezone.utc)
    return valor


def validar_base(base):
    if set(base) != set(TABELAS):
        raise ValueError("A base precisa conter as quatro tabelas do campeonato.")
    indices = {}
    for tabela, campos in TABELAS.items():
        for documento in base[tabela]:
            if set(documento) != {"_id", *campos[1:]}:
                raise ValueError(f"{tabela}: campos diferentes do modelo.")
            for campo in campos:
                valor = documento["_id" if campo == campos[0] else campo]
                if campo.startswith("id_") or campo in {"rodada", "minuto", "gols_mandante", "gols_visitante"}:
                    if valor is None and campo.startswith("gols_"):
                        continue
                    if not isinstance(valor, int) or isinstance(valor, bool):
                        raise ValueError(f"{tabela}.{campo}: esperado um inteiro BSON.")
                    converter_valor(campo, valor)
            for campo, limite in (("nome", 100), ("cidade", 80)):
                if campo not in documento or (campo == "cidade" and documento[campo] is None):
                    continue
                valor = documento[campo]
                if not isinstance(valor, str) or not valor.strip() or len(valor) > limite:
                    raise ValueError(f"{tabela}.{campo}: texto invalido.")
        indices[tabela] = {doc["_id"]: doc for doc in base[tabela]}
        if len(indices[tabela]) != len(base[tabela]):
            raise ValueError(f"{tabela}: identificador duplicado.")
    nomes = [clube["nome"] for clube in base["CLUBES"]]
    if len(nomes) != len(set(nomes)):
        raise ValueError("CLUBES: nomes duplicados.")
    for jogador in base["JOGADORES"]:
        if jogador["posicao"] not in ("Goleiro", "Zagueiro", "Lateral", "Volante", "Meio-Campo", "Atacante"):
            raise ValueError("JOGADORES: posicao invalida.")
        if jogador["id_clube"] not in indices["CLUBES"]:
            raise ValueError("JOGADORES: clube referenciado nao existe.")
    for partida in base["PARTIDAS"]:
        if any(partida[campo] not in indices["CLUBES"] for campo in ("id_mandante", "id_visitante")):
            raise ValueError("PARTIDAS: clube referenciado nao existe.")
        if partida["id_mandante"] == partida["id_visitante"]:
            raise ValueError("PARTIDAS: mandante e visitante devem ser diferentes.")
        data = partida["data_partida"]
        if (not isinstance(data, datetime) or any((data.hour, data.minute, data.second, data.microsecond))
                or data.utcoffset() not in (None, timezone.utc.utcoffset(data))):
            raise ValueError("PARTIDAS: esperado datetime a meia-noite UTC.")
        placar = (partida["gols_mandante"], partida["gols_visitante"])
        if partida["status"] == "ABERTA":
            if placar != (None, None):
                raise ValueError("PARTIDAS: placar deve ser nulo enquanto ABERTA.")
        elif partida["status"] != "FINALIZADA" or None in placar:
            raise ValueError("PARTIDAS: estado ou placar invalido.")
    for gol in base["GOLS"]:
        partida = indices["PARTIDAS"].get(gol["id_partida"])
        jogador = indices["JOGADORES"].get(gol["id_jogador"])
        if partida is None or jogador is None:
            raise ValueError("GOLS: partida ou jogador referenciado nao existe.")
        if jogador["id_clube"] not in (partida["id_mandante"], partida["id_visitante"]):
            raise ValueError("GOLS: jogador nao pertence aos clubes da partida.")


def ler_oracle(conexao):
    base = {}
    with conexao.cursor() as cursor:
        cursor.execute("SET TRANSACTION READ ONLY")
        for tabela, campos in TABELAS.items():
            cursor.execute(f"SELECT {', '.join(campos)} FROM {tabela} ORDER BY {campos[0]}")
            documentos = []
            while linhas := cursor.fetchmany(500):
                for linha in linhas:
                    documento = {
                        "_id" if indice == 0 else campo: converter_valor(campo, valor)
                        for indice, (campo, valor) in enumerate(zip(campos, linha))
                    }
                    documentos.append(documento)
            base[tabela] = documentos
    validar_base(base)
    return base


def migrar(base, banco, aplicar=False):
    validar_base(base)
    colecoes = set(banco.list_collection_names())
    resumo, uniao = {}, {}
    for tabela in TABELAS:
        documentos = list(banco[tabela].find({})) if tabela in colecoes else []
        existentes = {doc["_id"]: doc for doc in documentos}
        identicos = 0
        for documento in base[tabela]:
            anterior = existentes.get(documento["_id"])
            if anterior is not None:
                if anterior != documento:
                    raise ValueError(f"{tabela}: ID {documento['_id']} possui dados diferentes no destino.")
                identicos += 1
            else:
                existentes[documento["_id"]] = documento
        uniao[tabela] = list(existentes.values())
        resumo[tabela] = {"origem": len(base[tabela]), "identicos": identicos,
                          "novos": len(base[tabela]) - identicos, "inseridos": 0}
    validar_base(uniao)
    if aplicar:
        for tabela in TABELAS:
            if tabela not in colecoes:
                banco.create_collection(tabela)
            for documento in base[tabela]:
                resultado = banco[tabela].update_one(
                    {"_id": documento["_id"]}, {"$setOnInsert": documento}, upsert=True,
                )
                if resultado.upserted_id is not None:
                    resumo[tabela]["inseridos"] += 1
                if banco[tabela].find_one({"_id": documento["_id"]}) != documento:
                    raise ValueError(f"{tabela}: documento alterado durante a migracao.")
    return resumo


def main(argv=None):
    parser = argparse.ArgumentParser(description="Migracao Oracle para MongoDB do campeonato.")
    modos = parser.add_mutually_exclusive_group()
    modos.add_argument("--aplicar", action="store_true", help="Criar colecoes e inserir documentos.")
    modos.add_argument("--simular", action="store_true", help="Conferir dados sem gravar (padrao).")
    argumentos = parser.parse_args(argv)
    faltantes = [nome for nome in ("ORACLE_USER", "ORACLE_DSN", "MONGO_DATABASE") if not os.getenv(nome)]
    if faltantes:
        print("Configure as variaveis: " + ", ".join(faltantes), file=sys.stderr)
        return 2
    try:
        import oracledb
        from pymongo import MongoClient
    except ImportError:
        print("Instale as dependencias: python -m pip install -r requirements.txt", file=sys.stderr)
        return 2
    try:
        senha = os.getenv("ORACLE_PASSWORD")
        if senha is None:
            senha = getpass.getpass("Senha Oracle: ")
        with oracledb.connect(user=os.environ["ORACLE_USER"], password=senha,
                              dsn=os.environ["ORACLE_DSN"], tcp_connect_timeout=10) as conexao:
            conexao.call_timeout = 30000
            base = ler_oracle(conexao)
        with MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"),
                         serverSelectionTimeoutMS=10000, connectTimeoutMS=10000,
                         socketTimeoutMS=30000, tz_aware=True) as cliente:
            banco = cliente[os.environ["MONGO_DATABASE"]]
            if not banco.write_concern.acknowledged:
                raise ValueError("O MongoDB precisa confirmar as escritas (w >= 1).")
            cliente.admin.command("ping")
            resumo = migrar(base, banco, aplicar=argumentos.aplicar)
        print("Migracao concluida." if argumentos.aplicar else "Simulacao concluida: nenhuma escrita.")
        print("Colecao | Origem | Identicos | Novos previstos | Inseridos")
        for tabela, contagem in resumo.items():
            print(f"{tabela} | {contagem['origem']} | {contagem['identicos']} | "
                  f"{contagem['novos']} | {contagem['inseridos']}")
        return 0
    except ValueError as erro:
        print(str(erro), file=sys.stderr)
    except Exception as erro:
        print(f"Falha ({type(erro).__name__}). Confira conexoes, permissoes e tabelas.", file=sys.stderr)
    if argumentos.aplicar:
        print("Pode haver insercoes parciais. Mantenha a aplicacao parada, corrija a causa e simule antes de retomar.",
              file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
