/* Configuração pública: somente URL HTTPS e chave publicável/anon.
 * A segurança depende de RLS e permissões no banco. Nunca use service_role aqui.
 * Scripts clássicos permitem abrir index.html também via file://.
 */
(function (global) {
  'use strict';
  const CONFIG = Object.freeze({ url: '', publicKey: '' });
  const PAGE_SIZE = 1000;
  const MAX_ROWS = 100000;
  function isConfigured() { return Boolean(CONFIG.url && CONFIG.publicKey); }
  async function query(table, parameters, signal) {
    if (!isConfigured()) throw new Error('NOT_CONFIGURED');
    const base = new URL(CONFIG.url);
    if (base.protocol !== 'https:' || base.username || base.password) throw new Error('INVALID_CONFIG');
    if (CONFIG.publicKey.startsWith('sb_secret_')) throw new Error('INVALID_CONFIG');
    // Rejeita JWTs administrativos conhecidos. Isso não substitui as políticas RLS.
    const token = CONFIG.publicKey.split('.');
    if (token.length === 3) {
      try {
        const payload = JSON.parse(atob(token[1].replace(/-/g, '+').replace(/_/g, '/')));
        if (payload.role !== 'anon') throw new Error('INVALID_CONFIG');
      } catch (_) { throw new Error('INVALID_CONFIG'); }
    }
    const url = new URL('/rest/v1/' + table, base);
    url.search = new URLSearchParams(parameters).toString();
    const headers = { apikey: CONFIG.publicKey, Accept: 'application/json' };
    // Novas chaves sb_publishable_ não são JWTs e não vão em Authorization.
    if (token.length === 3) headers.Authorization = 'Bearer ' + CONFIG.publicKey;
    const response = await fetch(url, { headers, signal, cache: 'no-store' });
    if (!response.ok) throw new Error('QUERY_FAILED');
    const rows = await response.json();
    if (!Array.isArray(rows)) throw new Error('INVALID_RESPONSE');
    return rows;
  }
  async function allRows(table, params, signal) {
    const result = [];
    for (let offset = 0; offset < MAX_ROWS; offset += PAGE_SIZE) {
      const rows = await query(table, { ...params, limit: PAGE_SIZE, offset }, signal);
      result.push(...rows);
      if (rows.length < PAGE_SIZE) return result;
    }
    // Não apresenta um top 10 potencialmente incorreto por truncamento silencioso.
    throw new Error('RANKING_TOO_LARGE');
  }
  global.MilhaoAPI = Object.freeze({
    isConfigured,
    listGames: (signal) => allRows('jogos', { select: 'id,nome', order: 'id.asc' }, signal),
    listMatches: (gameId, signal) => allRows('partidas', {
      select: 'id,jogo_id,apelido,valor_ganho,tempo_segundos,data_hora',
      jogo_id: 'eq.' + gameId, order: 'id.asc'
    }, signal)
  });
})(window);
