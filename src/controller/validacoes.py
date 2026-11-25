LIMITE_INTEIRO = 2**63 - 1


def texto(valor, campo, limite, obrigatorio=True):
    if valor is None and not obrigatorio:
        return None
    if not isinstance(valor, str):
        raise ValueError(f"{campo} deve ser um texto.")
    valor = valor.strip()
    if not valor:
        if obrigatorio:
            raise ValueError(f"{campo} é obrigatório.")
        return None
    if len(valor) > limite:
        raise ValueError(f"{campo} deve ter no máximo {limite} caracteres.")
    return valor


def inteiro(valor, campo, minimo=1, maximo=LIMITE_INTEIRO):
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"{campo} deve ser um número inteiro.")
    if not minimo <= valor <= maximo:
        raise ValueError(f"{campo} deve estar entre {minimo} e {maximo}.")
    return valor


def proximo_id(colecao):
    ultimo = colecao.find_one({}, {"_id": 1}, sort=[("_id", -1)])
    if ultimo is None:
        return 1
    identificador = inteiro(ultimo["_id"], "_id existente")
    if identificador == LIMITE_INTEIRO:
        raise ValueError("O limite de identificadores desta coleção foi atingido.")
    return identificador + 1


def exigir_colecoes(banco, *nomes):
    existentes = set(banco.list_collection_names())
    if any(nome not in existentes for nome in nomes):
        raise ValueError("Coleção necessária ausente. Execute python -m src.criar_colecoes.")
