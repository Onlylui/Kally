-- 001: todas as tabelas do MVP, iguais ao Docs/banco.dbml.
-- A schema_versao não entra aqui: quem a cria é o aplicador de migrações (app/db.py).
-- Nunca edite esta migração depois de aplicada: mudanças vão num arquivo novo (002_...).

CREATE TABLE usuarios (
    telegram_id bigint PRIMARY KEY,
    nome        text NOT NULL,
    criado_em   timestamptz NOT NULL DEFAULT now()
);

-- Base de alimentos, valores por 100 g (RN-016, D-026).
CREATE TABLE alimentos (
    id            bigserial PRIMARY KEY,
    nome          text NOT NULL UNIQUE,
    kcal_100g     numeric NOT NULL CHECK (kcal_100g BETWEEN 0 AND 900),
    proteina_100g numeric NOT NULL CHECK (proteina_100g >= 0),
    carbo_100g    numeric NOT NULL CHECK (carbo_100g >= 0),
    gordura_100g  numeric NOT NULL CHECK (gordura_100g >= 0),
    porcao_g      numeric NOT NULL CHECK (porcao_g > 0),
    porcao_nome   text NOT NULL,
    origem        text NOT NULL DEFAULT 'ia' CHECK (origem IN ('ia', 'manual')),
    criado_em     timestamptz NOT NULL DEFAULT now()
);

-- Uma linha por /r ou /retro (D-022).
CREATE TABLE refeicoes (
    id            bigserial PRIMARY KEY,
    telegram_id   bigint NOT NULL REFERENCES usuarios (telegram_id),
    chat_id       bigint NOT NULL,
    message_id    bigint,
    descricao     text NOT NULL,
    kcal          integer NOT NULL CHECK (kcal >= 0),
    proteina_g    numeric NOT NULL CHECK (proteina_g >= 0),
    carbo_g       numeric NOT NULL CHECK (carbo_g >= 0),
    gordura_g     numeric NOT NULL CHECK (gordura_g >= 0),
    data          date NOT NULL,
    hora          time,
    retroativo    boolean NOT NULL DEFAULT false,
    kcal_manual   boolean NOT NULL DEFAULT false,
    registrado_em timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_refeicoes_usuario_data ON refeicoes (telegram_id, data);

-- Um alimento dentro de uma refeição (D-029).
CREATE TABLE refeicao_itens (
    id          bigserial PRIMARY KEY,
    refeicao_id bigint NOT NULL REFERENCES refeicoes (id) ON DELETE CASCADE,
    alimento_id bigint NOT NULL REFERENCES alimentos (id) ON DELETE RESTRICT,
    ordem       smallint NOT NULL,
    texto       text NOT NULL,
    gramas      numeric NOT NULL CHECK (gramas > 0),
    kcal        numeric NOT NULL,
    proteina_g  numeric NOT NULL,
    carbo_g     numeric NOT NULL,
    gordura_g   numeric NOT NULL
);

CREATE INDEX ix_itens_refeicao ON refeicao_itens (refeicao_id);
CREATE INDEX ix_itens_alimento ON refeicao_itens (alimento_id);

-- Pesagens do /peso (RN-012).
CREATE TABLE pesos (
    id            bigserial PRIMARY KEY,
    telegram_id   bigint NOT NULL REFERENCES usuarios (telegram_id),
    chat_id       bigint NOT NULL,
    message_id    bigint,
    peso_kg       numeric(5,2) NOT NULL CHECK (peso_kg BETWEEN 30 AND 300),
    data          date NOT NULL,
    hora          time NOT NULL,
    registrado_em timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_pesos_usuario_data ON pesos (telegram_id, data);
