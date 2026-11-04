(function () {
  'use strict';
  const api = window.MilhaoAPI;
  const ranking = window.MilhaoRanking;
  const filter = document.getElementById('jogo-filtro');
  const button = document.getElementById('atualizar');
  const status = document.getElementById('ranking-status');
  const table = document.getElementById('ranking-table-wrap');
  const body = document.getElementById('ranking-body');
  const updated = document.getElementById('ranking-updated');
  let activeRequest;
  function message(title, text) {
    table.hidden = true; body.replaceChildren(); status.hidden = false;
    status.querySelector('h3').textContent = title;
    status.querySelector('p').textContent = text;
  }
  async function refresh() {
    if (!api.isConfigured()) {
      message('O próximo destaque pode ser você.', 'O ranking aguarda configuração do Supabase. Os resultados aparecerão aqui quando a conexão estiver disponível.');
      return;
    }
    if (activeRequest) activeRequest.abort();
    const controller = new AbortController(); activeRequest = controller;
    const timer = setTimeout(() => controller.abort(), 20000);
    button.disabled = true; filter.disabled = true;
    document.querySelector('.ranking-panel').setAttribute('aria-busy', 'true');
    message('Consultando resultados…', 'Buscando os jogos e as melhores partidas.');
    try {
      const previous = filter.value;
      const games = await api.listGames(controller.signal);
      if (activeRequest !== controller) return;
      filter.replaceChildren();
      games.forEach(game => {
        const option = document.createElement('option');
        option.value = String(game.id); option.textContent = game.nome;
        filter.append(option);
      });
      if (!games.length) {
        const option = document.createElement('option'); option.value = ''; option.textContent = 'Nenhum jogo disponível'; filter.append(option);
        message('Ainda não há jogos.', 'Os jogos aparecerão aqui quando forem cadastrados pela equipe.');
        updated.textContent = 'Consulta concluída · nenhum jogo';
        return;
      }
      if (games.some(game => String(game.id) === previous)) filter.value = previous;
      const selected = games.find(game => String(game.id) === filter.value);
      const matches = await api.listMatches(filter.value, controller.signal);
      if (activeRequest !== controller) return;
      const rows = ranking.topTen(matches, filter.value);
      if (!rows.length) message('O pódio está esperando.', 'Este jogo ainda não tem partidas válidas no ranking.');
      else { ranking.render(body, rows, selected.nome); status.hidden = true; table.hidden = false; }
      updated.textContent = 'Atualizado às ' + new Intl.DateTimeFormat('pt-BR', { timeStyle: 'short', timeZone: 'America/Sao_Paulo' }).format(new Date()) + ' · Brasília';
    } catch (error) {
      if (activeRequest !== controller) return;
      message('Não foi possível carregar o ranking.', error.message === 'RANKING_TOO_LARGE'
        ? 'O volume de partidas exige uma consulta de ranking no servidor. Entre em contato com a equipe.'
        : 'A conexão não foi concluída. Tente atualizar novamente em instantes.');
      updated.textContent = 'Última consulta sem sucesso';
    } finally {
      clearTimeout(timer);
      if (activeRequest === controller) {
        button.disabled = false;
        filter.disabled = !filter.value;
        document.querySelector('.ranking-panel').setAttribute('aria-busy', 'false');
        activeRequest = null;
      }
    }
  }
  button.addEventListener('click', refresh);
  filter.addEventListener('change', refresh);
  refresh();
})();
