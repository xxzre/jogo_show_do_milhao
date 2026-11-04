# Show do Milhão — modo clássico

Jogo em Python com **nove perguntas** (3 fáceis, 3 médias e 3 difíceis), premiação substitutiva até R$ 1.000.000, ranking Supabase e quatro tipos de ajuda:

- **Cartas:** uma utilização por partida; elimina aleatoriamente de 0 a 3 alternativas incorretas.
- **Universitários:** uma utilização; três palpites simulados.
- **Plateia:** uma utilização; percentuais simulados que somam 100%.
- **Pulos:** três por partida; substitui a pergunta por outra da mesma dificuldade sem avançar a etapa.

## Rodar localmente

1. Instale Python e clone este repositório.
2. Instale as dependências: `python -m pip install -r requirements.txt`.
3. Copie `.env.example` para `.env`.
4. Preencha `SUPABASE_URL`, `SUPABASE_KEY` e `JOGO_ID=1`. **A chave secreta é exclusivamente para o backend/terminal**, nunca para frontend ou GitHub Pages.
5. Rode `python main.py`.

As tabelas estão descritas em `sql/schema.sql`. O banco deve ter pelo menos seis perguntas válidas de cada dificuldade (18 no total), para permitir até três pulos no mesmo nível. O banco configurado para esta implementação tem oito perguntas por nível.

## Testes

```bash
python -m unittest discover -s tests -v
```

Os testes não dependem de rede nem de credenciais.

## Segurança e próximos passos

O banco usa RLS e não concede acesso direto a `anon` e `authenticated`: a integração atual é **Python no servidor/terminal**, usando credencial secreta em ambiente seguro. Não hospede esse script com chave secreta em GitHub Pages. Para conectar uma página web, é necessário um backend/API com autenticação, validação dos resultados do lado do servidor, controle de estado por sessão e endpoint seguro para registrar pontos. **Ainda não há essa API nem interface web neste repositório**.

O jogo salva histórico de ajudas ao final da partida; se a partida não for persistida por falha de conexão, será necessário reenviá-la e depois sincronizar as ajudas. O fluxo de jogo roda pelo terminal; os resultados são simulados e não dependem de plateia real.
