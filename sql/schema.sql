-- =============================================================================
-- SCRIPT SQL COMPLETO - SHOW DO MILHÃO (SUPABASE)
-- Execute este script no SQL Editor do Supabase para criar/atualizar as tabelas
-- e liberar as permissões de Row Level Security (RLS) para o papel 'anon'.
-- =============================================================================

-- 1. TABELA DE JOGOS (Obrigatória para o filtro do site e vínculo com JOGO_ID)
CREATE TABLE IF NOT EXISTS public.jogos (
    id integer PRIMARY KEY,
    nome text NOT NULL CHECK (length(trim(nome)) > 0)
);

-- Garante que o jogo padrão (JOGO_ID = 1) exista na tabela 'jogos'
INSERT INTO public.jogos (id, nome)
VALUES (1, 'Show do Milhão')
ON CONFLICT (id) DO UPDATE SET nome = EXCLUDED.nome;

-- 2. TABELA DE PERGUNTAS
CREATE TABLE IF NOT EXISTS public.perguntas (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    enunciado text NOT NULL CHECK (length(trim(enunciado)) > 0),
    alternativa_a text NOT NULL,
    alternativa_b text NOT NULL,
    alternativa_c text NOT NULL,
    alternativa_d text NOT NULL,
    correta char(1) NOT NULL CHECK (correta IN ('A', 'B', 'C', 'D')),
    dificuldade text NOT NULL CHECK (dificuldade IN ('facil', 'media', 'dificil')),
    categoria text NOT NULL DEFAULT 'Conhecimentos gerais',
    ativa boolean NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS perguntas_dificuldade_idx
    ON public.perguntas(dificuldade) WHERE ativa;

-- 3. TABELA DE PARTIDAS (Contrato integrado Python <-> Site Ranking)
CREATE TABLE IF NOT EXISTS public.partidas (
    id uuid PRIMARY KEY,
    jogo_id integer NOT NULL REFERENCES public.jogos(id) ON DELETE CASCADE,
    apelido text NOT NULL CHECK (length(trim(apelido)) BETWEEN 1 AND 100),
    valor_ganho numeric(12,2) NOT NULL DEFAULT 0 CHECK (valor_ganho >= 0),
    tempo_segundos numeric(12,2) NOT NULL DEFAULT 0 CHECK (tempo_segundos >= 0),
    acertos integer NOT NULL DEFAULT 0 CHECK (acertos BETWEEN 0 AND 9),
    motivo_encerramento text NOT NULL CHECK (motivo_encerramento IN ('vitoria', 'erro', 'desistencia')),
    data_hora timestamptz NOT NULL DEFAULT now()
);

-- Índice otimizado para os critérios de desempate do Ranking:
-- 1º Maior valor_ganho (DESC), 2º Menor tempo_segundos (ASC), 3º data_hora (ASC), 4º id (ASC)
CREATE INDEX IF NOT EXISTS partidas_ranking_idx
    ON public.partidas(jogo_id, valor_ganho DESC, tempo_segundos ASC, data_hora ASC, id ASC);

-- 4. TABELA DE AJUDAS UTILIZADAS (Opcional / Histórico de telemetria da partida)
CREATE TABLE IF NOT EXISTS public.ajudas_utilizadas (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    partida_id uuid NOT NULL REFERENCES public.partidas(id) ON DELETE CASCADE,
    pergunta_id bigint NOT NULL REFERENCES public.perguntas(id),
    tipo text NOT NULL CHECK (tipo IN ('cartas', 'universitarios', 'plateia', 'pulo')),
    resultado jsonb NOT NULL DEFAULT '{}'::jsonb,
    utilizada_em timestamptz NOT NULL DEFAULT now(),
    UNIQUE(partida_id, pergunta_id, tipo)
);

CREATE INDEX IF NOT EXISTS ajudas_pergunta_idx ON public.ajudas_utilizadas(pergunta_id);
CREATE UNIQUE INDEX IF NOT EXISTS ajudas_unicas_por_partida
    ON public.ajudas_utilizadas(partida_id, tipo)
    WHERE tipo IN ('cartas', 'universitarios', 'plateia');

-- 5. TABELA DE ETAPAS DE PREMIAÇÃO
CREATE TABLE IF NOT EXISTS public.etapas_premiacao (
    etapa smallint PRIMARY KEY CHECK (etapa BETWEEN 1 AND 9),
    valor_premio numeric(12,2) NOT NULL CHECK (valor_premio > 0)
);

INSERT INTO public.etapas_premiacao (etapa, valor_premio) VALUES
    (1, 1000.00),
    (2, 5000.00),
    (3, 10000.00),
    (4, 25000.00),
    (5, 50000.00),
    (6, 100000.00),
    (7, 200000.00),
    (8, 500000.00),
    (9, 1000000.00)
ON CONFLICT (etapa) DO NOTHING;

-- =============================================================================
-- 6. PERMISSÕES E POLÍTICAS DE SEGURANÇA (ROW LEVEL SECURITY - RLS)
-- Corrige o bloqueio anterior (REVOKE ALL) que impedia o site e o cliente 'anon'
-- de lerem o ranking e gravarem as partidas finalizadas.
-- =============================================================================

-- Habilita RLS em todas as tabelas
ALTER TABLE public.jogos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.perguntas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.partidas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ajudas_utilizadas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.etapas_premiacao ENABLE ROW LEVEL SECURITY;

-- Concede acesso ao schema public para os papéis 'anon' e 'authenticated'
GRANT USAGE ON SCHEMA public TO anon, authenticated;

-- Concede permissões de leitura (SELECT) nas tabelas consultadas pelo jogo e pelo site
GRANT SELECT ON public.jogos TO anon, authenticated;
GRANT SELECT ON public.perguntas TO anon, authenticated;
GRANT SELECT ON public.etapas_premiacao TO anon, authenticated;

-- Concede SELECT, INSERT e UPDATE (necessário para o UPSERT idempotente) em 'partidas' e 'ajudas_utilizadas'
GRANT SELECT, INSERT, UPDATE ON public.partidas TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.ajudas_utilizadas TO anon, authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- Remove políticas antigas caso já existam (para permitir reexecução limpa deste script)
DROP POLICY IF EXISTS "Permitir SELECT publico em jogos" ON public.jogos;
DROP POLICY IF EXISTS "Permitir INSERT em jogos" ON public.jogos;
DROP POLICY IF EXISTS "Permitir SELECT publico em perguntas" ON public.perguntas;
DROP POLICY IF EXISTS "Permitir SELECT publico em partidas" ON public.partidas;
DROP POLICY IF EXISTS "Permitir INSERT publico em partidas" ON public.partidas;
DROP POLICY IF EXISTS "Permitir UPDATE idempotente em partidas" ON public.partidas;
DROP POLICY IF EXISTS "Permitir SELECT publico em ajudas_utilizadas" ON public.ajudas_utilizadas;
DROP POLICY IF EXISTS "Permitir INSERT publico em ajudas_utilizadas" ON public.ajudas_utilizadas;
DROP POLICY IF EXISTS "Permitir UPDATE idempotente em ajudas_utilizadas" ON public.ajudas_utilizadas;
DROP POLICY IF EXISTS "Permitir SELECT publico em etapas_premiacao" ON public.etapas_premiacao;

-- Políticas para a tabela 'jogos' (SELECT e INSERT para auto-cadastro se necessário)
CREATE POLICY "Permitir SELECT publico em jogos"
    ON public.jogos FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Permitir INSERT em jogos"
    ON public.jogos FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- Políticas para a tabela 'perguntas' (SELECT para carregar perguntas no jogo Python)
CREATE POLICY "Permitir SELECT publico em perguntas"
    ON public.perguntas FOR SELECT
    TO anon, authenticated
    USING (true);

-- Políticas para a tabela 'partidas' (SELECT para o site/ranking e INSERT/UPDATE para o jogo Python)
CREATE POLICY "Permitir SELECT publico em partidas"
    ON public.partidas FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Permitir INSERT publico em partidas"
    ON public.partidas FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "Permitir UPDATE idempotente em partidas"
    ON public.partidas FOR UPDATE
    TO anon, authenticated
    USING (true)
    WITH CHECK (true);

-- Políticas para a tabela 'ajudas_utilizadas'
CREATE POLICY "Permitir SELECT publico em ajudas_utilizadas"
    ON public.ajudas_utilizadas FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Permitir INSERT publico em ajudas_utilizadas"
    ON public.ajudas_utilizadas FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "Permitir UPDATE idempotente em ajudas_utilizadas"
    ON public.ajudas_utilizadas FOR UPDATE
    TO anon, authenticated
    USING (true)
    WITH CHECK (true);

-- Políticas para a tabela 'etapas_premiacao'
CREATE POLICY "Permitir SELECT publico em etapas_premiacao"
    ON public.etapas_premiacao FOR SELECT
    TO anon, authenticated
    USING (true);
