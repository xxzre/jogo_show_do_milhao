(function (global) {
  'use strict';
  const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const date = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' });
  const compareText = (a, b) => a < b ? -1 : a > b ? 1 : 0;
  function compare(a, b) {
    return Number(b.valor_ganho) - Number(a.valor_ganho)
      || Number(a.tempo_segundos) - Number(b.tempo_segundos)
      || Date.parse(a.data_hora) - Date.parse(b.data_hora)
      || compareText(String(a.id), String(b.id));
  }
  function topTen(matches, gameId) {
    const valid = matches.filter(row => String(row.jogo_id) === String(gameId)
      && row.id != null && typeof row.apelido === 'string' && row.apelido.trim()
      && row.valor_ganho != null && row.valor_ganho !== '' && Number.isFinite(Number(row.valor_ganho)) && Number(row.valor_ganho) >= 0
      && row.tempo_segundos != null && row.tempo_segundos !== '' && Number.isFinite(Number(row.tempo_segundos)) && Number(row.tempo_segundos) >= 0
      && Number.isFinite(Date.parse(row.data_hora)));
    const seen = new Set();
    return valid.sort(compare).filter(row => {
      // Apelidos iguais após NFC e remoção de espaços nas pontas; caixa é preservada.
      const key = row.apelido.trim().normalize('NFC');
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }).slice(0, 10);
  }
  function render(body, rows, gameName) {
    body.replaceChildren();
    rows.forEach((row, index) => {
      const tr = document.createElement('tr');
      if (index < 3) tr.className = 'top-' + (index + 1);
      const place = document.createElement('td');
      const badge = document.createElement('span');
      badge.className = 'place'; badge.textContent = (index + 1) + 'º';
      place.append(badge); tr.append(place);
      const seconds = Number(row.tempo_segundos);
      const duration = Math.floor(seconds / 60) + 'min ' + (seconds % 60).toLocaleString('pt-BR', { maximumFractionDigits: 2 }) + 's';
      [gameName, row.apelido, money.format(Number(row.valor_ganho)), duration, date.format(new Date(row.data_hora))].forEach(value => {
        const td = document.createElement('td'); td.textContent = value; tr.append(td);
      });
      body.append(tr);
    });
  }
  global.MilhaoRanking = Object.freeze({ topTen, compare, render });
})(window);
