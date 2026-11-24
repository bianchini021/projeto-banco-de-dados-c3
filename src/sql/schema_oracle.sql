CREATE TABLE CLUBES (
    id_clube NUMBER(19,0) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome VARCHAR2(100 CHAR) NOT NULL UNIQUE,
    cidade VARCHAR2(80 CHAR)
);

CREATE TABLE JOGADORES (
    id_jogador NUMBER(19,0) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome VARCHAR2(100 CHAR) NOT NULL,
    posicao VARCHAR2(20 CHAR) NOT NULL,
    id_clube NUMBER(19,0) NOT NULL,
    CONSTRAINT fk_jogadores_clube FOREIGN KEY (id_clube) REFERENCES CLUBES(id_clube),
    CONSTRAINT chk_posicao_valida CHECK (
        posicao IN ('Goleiro', 'Zagueiro', 'Lateral', 'Volante', 'Meio-Campo', 'Atacante')
    )
);

CREATE TABLE PARTIDAS (
    id_partida NUMBER(19,0) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_mandante NUMBER(19,0) NOT NULL,
    id_visitante NUMBER(19,0) NOT NULL,
    rodada NUMBER(10,0) NOT NULL,
    data_partida DATE NOT NULL,
    status VARCHAR2(10 CHAR) DEFAULT 'ABERTA' NOT NULL,
    gols_mandante NUMBER(10,0),
    gols_visitante NUMBER(10,0),
    CONSTRAINT fk_partidas_mandante FOREIGN KEY (id_mandante) REFERENCES CLUBES(id_clube),
    CONSTRAINT fk_partidas_visitante FOREIGN KEY (id_visitante) REFERENCES CLUBES(id_clube),
    CONSTRAINT chk_times_diferentes CHECK (id_mandante <> id_visitante),
    CONSTRAINT chk_rodada_positiva CHECK (rodada > 0),
    CONSTRAINT chk_status_valido CHECK (status IN ('ABERTA', 'FINALIZADA')),
    CONSTRAINT chk_data_sem_horario CHECK (data_partida = TRUNC(data_partida)),
    CONSTRAINT chk_estado_placar CHECK (
        (status = 'ABERTA' AND gols_mandante IS NULL AND gols_visitante IS NULL) OR
        (status = 'FINALIZADA' AND gols_mandante IS NOT NULL AND gols_mandante >= 0
         AND gols_visitante IS NOT NULL AND gols_visitante >= 0)
    )
);

CREATE TABLE GOLS (
    id_gol NUMBER(19,0) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_partida NUMBER(19,0) NOT NULL,
    id_jogador NUMBER(19,0) NOT NULL,
    minuto NUMBER(3,0) NOT NULL,
    CONSTRAINT fk_gols_partida FOREIGN KEY (id_partida) REFERENCES PARTIDAS(id_partida),
    CONSTRAINT fk_gols_jogador FOREIGN KEY (id_jogador) REFERENCES JOGADORES(id_jogador),
    CONSTRAINT chk_minuto_valido CHECK (minuto BETWEEN 1 AND 130)
);
