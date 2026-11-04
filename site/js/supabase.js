/* Configuração pública do Supabase para o site de Ranking (GitHub Pages).
 * IMPORTANTE: Preencha 'url' e 'publicKey' exatamente com os mesmos valores de
 * SUPABASE_URL e SUPABASE_KEY (chave pública 'anon' ou 'sb_publishable_...')
 * utilizados no arquivo .env do módulo Python.
 * Nunca utilize a chave 'service_role' / 'sb_secret_' no front-end público.
 */
(function (global) {
  'use strict';

  const CONFIG = Object.freeze({
    // Exemplo: 'https://seu-projeto.supabase.co'
    url: 'https://seu-projeto.supabase.co',
    // Exemplo: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' (anon key) ou 'sb_publishable_...'
    publicKey: 'sua-anon-key-aqui',
    // Mesmo JOGO_ID configurado no .env do Python (padrão: 1)
    defaultGameId: 1
  });

  const PAGE_SIZE = 1000;
  const MAX_ROWS = 100000;

  function isConfigured() {
    const urlValida = Boolean(
      CONFIG.url &&
      CONFIG.url !== 'https://seu-projeto.supabase.co' &&
      CONFIG.url.trim() !== ''
    );
    const keyValida = Boolean(
      CONFIG.publicKey &&
      CONFIG.publicKey !== 'sua-anon-key-aqui' &&
      CONFIG.publicKey.trim() !== ''
    );
    return urlValida && keyValida;
  }

  async function query(table, parameters, signal) {
    if (!isConfigured()) {
      console.warn('[ShowDoMilhao][SupabaseJS] Credenciais ainda não configuradas em site/js/supabase.js.');
      throw new Error('NOT_CONFIGURED');
    }

    let base;
    try {
      base = new URL(CONFIG.url);
    } catch (_) {
      throw new Error('INVALID_CONFIG: SUPABASE_URL malformada.');
    }

    if (base.protocol !== 'https:' || base.username || base.password) {
      throw new Error('INVALID_CONFIG: SUPABASE_URL deve usar HTTPS.');
    }
    if (CONFIG.publicKey.startsWith('sb_secret_')) {
      throw new Error('INVALID_CONFIG: Não use chave secreta (sb_secret_) no navegador. Use a chave anon/publicável.');
    }

    // Verifica se é um JWT e bloqueia caso seja service_role
    const token = CONFIG.publicKey.split('.');
    if (token.length === 3) {
      try {
        const payload = JSON.parse(atob(token[1].replace(/-/g, '+').replace(/_/g, '/')));
        if (payload.role && payload.role !== 'anon') {
          throw new Error('INVALID_CONFIG: A chave JWT informada não possui role "anon".');
        }
      } catch (err) {
        if (err.message && err.message.startsWith('INVALID_CONFIG')) throw err;
        throw new Error('INVALID_CONFIG: Token JWT inválido em publicKey.');
      }
    }

    const url = new URL('/rest/v1/' + table, base);
    url.search = new URLSearchParams(parameters).toString();

    const headers = {
      apikey: CONFIG.publicKey,
      Accept: 'application/json'
    };
    if (token.length === 3) {
      headers.Authorization = 'Bearer ' + CONFIG.publicKey;
    }

    console.log(`[ShowDoMilhao][SupabaseJS] Consultando tabela "${table}":`, url.toString());

    let response;
    try {
      response = await fetch(url, { headers, signal, cache: 'no-store' });
    } catch (networkErr) {
      console.error(`[ShowDoMilhao][SupabaseJS] Falha de rede ao consultar "${table}":`, networkErr);
      throw new Error('NETWORK_ERROR: Falha de conexão com o Supabase (' + networkErr.message + ')');
    }

    console.log(`[ShowDoMilhao][SupabaseJS] Status HTTP (${table}):`, response.status, response.statusText);

    if (!response.ok) {
      let errorDetail = '';
      try {
        const errJson = await response.json();
        console.error(`[ShowDoMilhao][SupabaseJS] Erro retornado pela API (${table}):`, errJson);
        errorDetail = errJson.message || errJson.details || errJson.hint || JSON.stringify(errJson);
      } catch (_) {
        errorDetail = response.statusText;
      }

      if (response.status === 401 || response.status === 403) {
        throw new Error(
          `RLS_PERMISSION_DENIED (HTTP ${response.status}) na tabela "${table}": ${errorDetail}. ` +
          `Execute o script sql/schema.sql no Supabase para liberar SELECT para a role "anon".`
        );
      }
      if (response.status === 404) {
        throw new Error(
          `TABLE_NOT_FOUND (HTTP 404): A tabela "${table}" não foi encontrada no Supabase (${errorDetail}).`
        );
      }
      throw new Error(`QUERY_FAILED (HTTP ${response.status} em "${table}"): ${errorDetail}`);
    }

    const rows = await response.json();
    console.log(`[ShowDoMilhao][SupabaseJS] Dados recebidos de "${table}" (${Array.isArray(rows) ? rows.length : 0} registros):`, rows);

    if (!Array.isArray(rows)) {
      throw new Error('INVALID_RESPONSE: A resposta do Supabase não é uma lista JSON.');
    }
    return rows;
  }

  async function allRows(table, params, signal) {
    const result = [];
    for (let offset = 0; offset < MAX_ROWS; offset += PAGE_SIZE) {
      const rows = await query(table, { ...params, limit: PAGE_SIZE, offset }, signal);
      result.push(...rows);
      if (rows.length < PAGE_SIZE) return result;
    }
    throw new Error('RANKING_TOO_LARGE');
  }

  async function listGames(signal) {
    try {
      const games = await allRows('jogos', { select: 'id,nome', order: 'id.asc' }, signal);
      if (games.length > 0) {
        return games;
      }
      console.warn(
        '[ShowDoMilhao][SupabaseJS] Tabela "jogos" está vazia. Usando JOGO_ID padrão:',
        CONFIG.defaultGameId
      );
      return [{ id: CONFIG.defaultGameId, nome: 'Show do Milhão (Jogo ' + CONFIG.defaultGameId + ')' }];
    } catch (err) {
      console.warn(
        '[ShowDoMilhao][SupabaseJS] Não foi possível listar a tabela "jogos" (' + err.message + '). ' +
        'Utilizando fallback para JOGO_ID=' + CONFIG.defaultGameId
      );
      return [{ id: CONFIG.defaultGameId, nome: 'Show do Milhão (Jogo ' + CONFIG.defaultGameId + ')' }];
    }
  }

  async function listMatches(gameId, signal) {
    const targetGameId = gameId || CONFIG.defaultGameId;
    return allRows('partidas', {
      select: 'id,jogo_id,apelido,valor_ganho,tempo_segundos,acertos,motivo_encerramento,data_hora',
      jogo_id: 'eq.' + targetGameId,
      order: 'valor_ganho.desc,tempo_segundos.asc,data_hora.asc,id.asc'
    }, signal);
  }

  global.MilhaoAPI = Object.freeze({
    CONFIG,
    isConfigured,
    listGames,
    listMatches
  });
})(window);
