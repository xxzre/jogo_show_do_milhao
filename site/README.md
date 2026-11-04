# Show do Milhão — site

Front-end estático em HTML, CSS e JavaScript puro. Não inicia nem altera o jogo Python. Sem dependências, build, CDN, fontes externas ou credenciais pré-preenchidas.

## Visualizar

Abra `site/index.html` no navegador. Para testar também as requisições do Supabase, prefira um servidor estático: na raiz do repositório, execute `python3 -m http.server 8000 --directory site` e abra o endereço local indicado pelo servidor. Nenhum processo é necessário para publicar os arquivos no Pages.

Arquivos:

- `index.html`: início, regras, premiações e ranking acessível.
- `css/style.css`: identidade azul e dourada, layout responsivo e movimento reduzido.
- `js/supabase.js`: configuração e consultas REST GET paginadas.
- `js/ranking.js`: classificação, deduplicação e renderização segura.
- `js/app.js`: filtro, atualização, timeout e estados da interface.
- `assets/emblema.svg`: emblema original local.

## Conectar o Supabase

A equipe de banco deve fornecer a URL HTTPS do projeto, uma chave **publicável** (`sb_publishable_…`) ou a antiga chave `anon`, e preparar:

- `jogos`: `id`, `nome`.
- `partidas`: `id`, `jogo_id`, `apelido`, `valor_ganho`, `tempo_segundos`, `acertos`, `motivo_encerramento`, `data_hora`.

Preencha somente `url` e `publicKey` em `CONFIG` no arquivo `js/supabase.js`. A chave publicável é visível no código do navegador por definição. Nunca coloque `service_role`, chave secreta ou senha no site. Sem configuração, nenhuma chamada é feita e a interface informa que aguarda configuração.

**Contrato obrigatório de segurança do banco:** habilitar RLS e conceder ao papel `anon` somente SELECT para os resultados públicos necessários. Revogar INSERT, UPDATE, DELETE e acesso a gabaritos/perguntas privadas. Restringir também as colunas consultáveis se houver outras informações nas tabelas. Não basta esconder botões: qualquer visitante pode enviar suas próprias requisições. As políticas e permissões são responsabilidade da equipe de integração; este site não as cria. Não publique a conexão antes de verificá-las. O navegador não autentica jogadores nem grava partidas.

As consultas leem `jogos(id,nome)` e `partidas(id,jogo_id,apelido,valor_ganho,tempo_segundos,data_hora)` filtradas pelo jogo. Não consultam `perguntas`. Use datas ISO 8601 com fuso e valores numéricos não negativos; as datas são exibidas em America/Sao_Paulo. IDs de partidas devem ser únicos e estáveis.

A classificação é: prêmio decrescente, duração crescente, instante da data crescente e ID crescente (comparação textual determinística). Ordenamos todas as partidas do jogo, selecionamos a melhor por apelido e depois os primeiros dez. Apelidos são comparados após normalização Unicode NFC e remoção de espaços nas pontas; maiúsculas e minúsculas são distintas. Registros inválidos são omitidos. Não há critério de acertos no desempate.

O cliente busca páginas de 1.000 linhas, com ordem estável por ID. Configure o limite REST do Supabase para **pelo menos 1.000 linhas**, senão a paginação poderá ser encerrada cedo. A partir de 100.000 registros consultados, a interface exige uma consulta no servidor em vez de exibir resultados potencialmente truncados. Para grandes volumes, a equipe deve implementar uma view/RPC com deduplicação e top 10 no banco e adaptar `listMatches`/`topTen`. Leituras em páginas não são uma transação: partidas inseridas durante a consulta podem exigir uma atualização para aparecer.

Em ambientes de rede restrita, permita o domínio exato do projeto Supabase. Não são necessários segredos de ambiente para o site estático; substituição de variáveis de ambiente não acontece automaticamente no navegador.

## Publicar no GitHub Pages

### Publicação pela main e pela raiz

Em **Settings → Pages → Build and deployment**, selecione **Deploy from a branch**, branch **main** e pasta **/(root)**, e salve. O `index.html` da raiz encaminha automaticamente para `./site/`, mantendo os arquivos do Front-end organizados nessa pasta. Não há build ou instalação de dependências.

Após o workflow **pages build and deployment** concluir, abra:

- Página inicial: <https://xxzre.github.io/jogo_show_do_milhao/>
- Acesso direto ao site: <https://xxzre.github.io/jogo_show_do_milhao/site/>

A aba **Actions** mostra as execuções de publicação, não a interface do site. O botão **Visit site** em **Settings → Pages** abre a página publicada. Se estiver vendo uma versão anterior, confirme o commit da última publicação e atualize o navegador com `Ctrl+F5`.

### Alternativa: publicar somente a pasta site com Actions

Os caminhos são relativos e também funcionam ao publicar apenas o conteúdo de `site/` na raiz do endereço Pages. O GitHub Pages não permite selecionar `site/` diretamente em “Deploy from a branch” (as opções são raiz e `docs/`). Para publicar somente essa pasta, substitua o modo de publicação por Actions:

1. Com autorização da equipe, crie `.github/workflows/pages.yml` na raiz usando o exemplo abaixo. Ele não foi adicionado automaticamente para não ativar publicação no repositório compartilhado.
2. Em **Settings → Pages → Build and deployment**, selecione **GitHub Actions**.
3. Faça commit e push dos arquivos e do workflow somente com autorização. Execute o workflow na aba Actions. O exemplo é manual e publica o conteúdo de `site/`.

```yaml
name: Publicar site
on:
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
      - name: Publicar
        id: deployment
        uses: actions/deploy-pages@v4
```

## Verificação após integração

Em um projeto de teste preparado pela equipe de banco (não pelo navegador público):

1. Cadastre dois jogos e partidas com apelidos repetidos. Verifique que aparece só a melhor partida por apelido em cada jogo.
2. Cadastre mais de dez apelidos e empates de prêmio, tempo e data; confirme o desempate por ID e o limite de dez. Inclua mais de 1.000 partidas para verificar paginação.
3. Troque o jogo no filtro e atualize. Verifique um jogo vazio, desconexão, resposta negada e timeout. Resultados anteriores não devem ficar visíveis como se fossem atuais após falha.
4. Use um apelido como `<img src=x onerror=alert(1)>`: deve aparecer somente como texto.
5. Confira os três primeiros lugares, moeda, duração e datas, navegação por teclado e telas pequenas.
6. Com a chave pública, a equipe deve confirmar SELECT permitido somente para resultados públicos e POST/PATCH/DELETE negados, além de acesso a gabaritos negado. Faça testes de escrita apenas no banco de teste e com autorização da equipe.

Não há resultados de demonstração na página. A integração real, políticas RLS e persistência permanecem sob responsabilidade dos outros integrantes.
