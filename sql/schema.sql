-- Estrutura do Show do Milhão (9 perguntas).
-- Espelha a migração aplicada ao projeto Supabase.
CREATE TABLE IF NOT EXISTS public.perguntas (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 enunciado text NOT NULL CHECK (length(trim(enunciado)) > 0),
 alternativa_a text NOT NULL,
 alternativa_b text NOT NULL,
 alternativa_c text NOT NULL,
 alternativa_d text NOT NULL,
 correta char(1) NOT NULL CHECK (correta IN ('A','B','C','D')),
 dificuldade text NOT NULL CHECK (dificuldade IN ('facil','media','dificil')),
 categoria text NOT NULL DEFAULT 'Conhecimentos gerais',
 ativa boolean NOT NULL DEFAULT true
);
CREATE INDEX IF NOT EXISTS perguntas_dificuldade_idx ON public.perguntas(dificuldade) WHERE ativa;
CREATE TABLE IF NOT EXISTS public.partidas (
 id uuid PRIMARY KEY,
 jogo_id integer NOT NULL,
 apelido text NOT NULL CHECK (length(trim(apelido)) BETWEEN 1 AND 100),
 valor_ganho numeric(12,2) NOT NULL DEFAULT 0 CHECK (valor_ganho >= 0),
 tempo_segundos numeric(12,2) NOT NULL DEFAULT 0 CHECK (tempo_segundos >= 0),
 acertos integer NOT NULL DEFAULT 0 CHECK (acertos BETWEEN 0 AND 9),
 motivo_encerramento text NOT NULL CHECK (motivo_encerramento IN ('vitoria','erro','desistencia')),
 data_hora timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS partidas_ranking_idx ON public.partidas(jogo_id,valor_ganho DESC,acertos DESC,tempo_segundos ASC);
CREATE TABLE IF NOT EXISTS public.ajudas_utilizadas (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 partida_id uuid NOT NULL REFERENCES public.partidas(id) ON DELETE CASCADE,
 pergunta_id bigint NOT NULL REFERENCES public.perguntas(id),
 tipo text NOT NULL CHECK (tipo IN ('cartas','universitarios','plateia','pulo')),
 resultado jsonb NOT NULL DEFAULT '{}'::jsonb,
 utilizada_em timestamptz NOT NULL DEFAULT now(),
 UNIQUE(partida_id,pergunta_id,tipo)
);
CREATE INDEX IF NOT EXISTS ajudas_pergunta_idx ON public.ajudas_utilizadas(pergunta_id);
CREATE UNIQUE INDEX IF NOT EXISTS ajudas_unicas_por_partida ON public.ajudas_utilizadas(partida_id,tipo)
 WHERE tipo IN ('cartas','universitarios','plateia');
CREATE TABLE IF NOT EXISTS public.etapas_premiacao (
 etapa smallint PRIMARY KEY CHECK(etapa BETWEEN 1 AND 9),
 valor_premio numeric(12,2) NOT NULL CHECK(valor_premio > 0)
);
INSERT INTO public.etapas_premiacao(etapa,valor_premio) VALUES
 (1,1000),(2,5000),(3,10000),(4,25000),(5,50000),
 (6,100000),(7,200000),(8,500000),(9,1000000)
ON CONFLICT (etapa) DO NOTHING;
ALTER TABLE public.perguntas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.partidas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ajudas_utilizadas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.etapas_premiacao ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.perguntas,public.partidas,public.ajudas_utilizadas,public.etapas_premiacao FROM anon,authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon,authenticated;
-- Acesso apenas por chave secreta em backend confiável.
