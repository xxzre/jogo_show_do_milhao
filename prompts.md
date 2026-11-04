# Registro de Prompts e Evolução Técnica — Show do Milhão (Python + Supabase + GitHub Pages)

Este documento registra os prompts utilizados no desenvolvimento e diagnóstico de integração do projeto acadêmico **Show do Milhão**, bem como as decisões arquiteturais e correções aplicadas.

---

## Prompt 1 — Desenvolvimento do Módulo do Jogo em Python (Terminal) Integrado ao Supabase

### Contexto / Solicitação
Desenvolvimento modular em Python 3.10+ para execução no terminal integrado ao Supabase (`supabase-py`), contendo:
- Validação de apelido não vazio.
- Sorteio de 9 perguntas (3 fáceis, 3 médias e 3 difíceis) + reservas para pulos, sem repetição.
- Sistema de ajudas (Cartas, Universitários, Plateia e Pulos).
- Tabela de prêmios substitutivos (de R$ 1.000,00 até R$ 1.000.000,00).
- Medição precisa de tempo com `time.perf_counter()`.
- Persistência idempotente de partidas com `uuid.uuid4()` gerado localmente e fila de reintento em memória em caso de falha de rede.

### Arquivos Estruturados
- `config.py`, `database.py`, `game_logic.py`, `ajudas.py`, `main.py`, `requirements.txt`, `.env.example`.

---

## Prompt 2 — Diagnóstico e Correção de Sincronização entre Python, Supabase e Ranking Web (GitHub Pages)

### Problema Relatado
> *"Estou com um problema de sincronização entre o meu jogo em Python (Show do Milhão) e o site de ranking publicado no GitHub Pages (`https://xxzre.github.io/jogo_show_do_milhao/`). O jogo no terminal roda, mas os dados das partidas finalizadas não estão refletindo na tabela de ranking da página web. Preciso que você diagnostique a causa e forneça as correções necessárias para alinhar o código em Python com o front-end JavaScript do site."*

### Diagnóstico de Causa Raiz (4 Gargalos Identificados)
1. **Credenciais vazias no Front-End (`site/js/supabase.js`)**:
   - O objeto `CONFIG` no arquivo `site/js/supabase.js` estava com `url: ''` e `publicKey: ''`, fazendo `isConfigured()` retornar `false` e impedindo qualquer requisição HTTP ao Supabase.
2. **Bloqueio de Row Level Security (RLS) e `REVOKE ALL` no Banco (`sql/schema.sql`)**:
   - O script `sql/schema.sql` habilitava RLS em todas as tabelas e executava `REVOKE ALL ... FROM anon, authenticated` sem criar políticas (`CREATE POLICY`) para o papel `anon`. Assim, tanto o navegador quanto o cliente Python usando a chave `anon` recebiam erro de permissão (`HTTP 401/403 - permission denied`).
3. **Ausência da Tabela `jogos` no Script SQL (`sql/schema.sql`)**:
   - O site consulta primeiro a tabela `jogos` (`SELECT id, nome FROM jogos`) para popular o seletor de jogos antes de buscar `partidas`. O script `sql/schema.sql` original não criava a tabela `public.jogos` nem inseria o registro inicial (`id = 1, nome = 'Show do Milhão'`).
4. **Alinhamento de Critérios de Desempate e Deduplicação (`database.py` vs `site/js/ranking.js`)**:
   - Adicionada validação automática do `jogo_id` na tabela `jogos`, logs detalhados de status HTTP/PostgREST em `database.py`, e alinhamento da consulta do ranking para aplicar os 4 critérios oficiais (`valor_ganho DESC`, `tempo_segundos ASC`, `data_hora ASC`, `id ASC`) mantendo apenas a melhor partida de cada `apelido` (Top 10).
