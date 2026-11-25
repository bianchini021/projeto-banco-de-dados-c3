import os

from pymongo import MongoClient
from pymongo.errors import PyMongoError


class MongoQueries:
    def __init__(self):
        self.mongo_client = None
        self.db = None

    def connect(self):
        if self.mongo_client is not None:
            return self.db

        nome_banco = os.getenv("MONGO_DATABASE", "").strip()
        if not nome_banco:
            raise ValueError("Configure a variável MONGO_DATABASE.")

        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        if not uri.strip():
            raise ValueError("MONGO_URI não pode estar vazia.")

        try:
            self.mongo_client = MongoClient(
                uri,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                tz_aware=True,
            )
            self.db = self.mongo_client[nome_banco]
            if not self.db.write_concern.acknowledged:
                raise ValueError("O MongoDB precisa confirmar as escritas (w >= 1).")
            self.mongo_client.admin.command("ping")
            return self.db
        except (PyMongoError, ValueError):
            self.close()
            raise ConnectionError(
                "Não foi possível conectar ao MongoDB. Confira MONGO_URI, "
                "MONGO_DATABASE, autenticação e disponibilidade do servidor. "
                "A conexão deve confirmar as escritas (w >= 1)."
            ) from None

    def close(self):
        try:
            if self.mongo_client is not None:
                self.mongo_client.close()
        finally:
            self.mongo_client = None
            self.db = None
