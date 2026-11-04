"""
Módulo de acesso a dados e integração com o Supabase.
Gerencia a conexão, sorteio de perguntas por dificuldade, consulta ao ranking
e persistência idempotente de partidas com suporte a reintento em caso de falha.
"""

import random
from typing import Any
from supabase import Client, create_client

from config import AppConfig


class DatabaseError(Exception):
    """Exceção geral para falhas de comunicação ou consulta ao banco de dados."""
    pass


class PerguntasInsuficientesError(DatabaseError):
    """Exceção específica para quando o banco não possui perguntas suficientes."""
    pass


class SupabaseRepository:
    """Repositório responsável pelas operações no banco de dados Supabase."""

    DIFICULDADES_ORDEM: tuple[tuple[str, int], ...] = (
        ("facil", 6),
        ("media", 6),
        ("dificil", 6),
    )

    CAMPOS_OBRIGATORIOS_PERGUNTA: set[str] = {
        "id",
        "enunciado",
        "alternativa_a",
        "alternativa_b",
        "alternativa_c",
        "alternativa_d",
        "correta",
        "dificuldade",
    }

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        try:
            self.client: Client = create_client(config.supabase_url, config.supabase_key)
        except Exception as exc:
            raise DatabaseError(
                f"Falha ao inicializar o cliente do Supabase: {exc}"
            ) from exc

    def _validar_pergunta(self, registro: dict[str, Any]) -> dict[str, Any] | None:
        """
        Valida e sanitiza um registro de pergunta vindo do banco.
        Retorna None caso o registro esteja incompleto ou com alternativa correta inválida.
        """
        if not self.CAMPOS_OBRIGATORIOS_PERGUNTA.issubset(registro.keys()):
            return None

        correta = str(registro.get("correta", "")).strip().upper()
        if correta not in ("A", "B", "C", "D"):
            return None

        enunciado = str(registro.get("enunciado", "")).strip()
        if not enunciado:
            return None

        return {
            "id": registro["id"],
            "enunciado": enunciado,
            "alternativa_a": str(registro.get("alternativa_a", "")).strip(),
            "alternativa_b": str(registro.get("alternativa_b", "")).strip(),
            "alternativa_c": str(registro.get("alternativa_c", "")).strip(),
            "alternativa_d": str(registro.get("alternativa_d", "")).strip(),
            "correta": correta,
            "dificuldade": str(registro.get("dificuldade", "")).strip().lower(),
        }

    def buscar_perguntas_partida(self) -> list[dict[str, Any]]:
        """
        Busca 18 perguntas sem repetição: 6 por dificuldade.
        Três de cada nível serão usadas e três ficarão de reserva para pulos.

        Returns:
            list[dict[str, Any]]: Lista ordenada com as 9 perguntas da partida.

        Raises:
            PerguntasInsuficientesError: Se faltar quantidade mínima em alguma dificuldade.
            DatabaseError: Se houver erro de rede, permissão ou timeout no Supabase.
        """
        perguntas_selecionadas: list[dict[str, Any]] = []
        ids_ja_utilizados: set[Any] = set()

        try:
            for dificuldade, quantidade_necessaria in self.DIFICULDADES_ORDEM:
                resposta = (
                    self.client.table("perguntas")
                    .select(
                        "id, enunciado, alternativa_a, alternativa_b, "
                        "alternativa_c, alternativa_d, correta, dificuldade"
                    )
                    .eq("dificuldade", dificuldade)
                    .execute()
                )

                dados = resposta.data or []
                perguntas_validas: list[dict[str, Any]] = []

                for item in dados:
                    pergunta_limpa = self._validar_pergunta(item)
                    if pergunta_limpa and pergunta_limpa["id"] not in ids_ja_utilizados:
                        perguntas_validas.append(pergunta_limpa)

                if len(perguntas_validas) < quantidade_necessaria:
                    raise PerguntasInsuficientesError(
                        f"Banco de dados possui apenas {len(perguntas_validas)} pergunta(s) "
                        f"válida(s) de nível '{dificuldade}', mas são necessárias pelo menos "
                        f"{quantidade_necessaria} para iniciar a partida."
                    )

                sorteadas = random.sample(perguntas_validas, quantidade_necessaria)
                for p in sorteadas:
                    ids_ja_utilizados.add(p["id"])
                    perguntas_selecionadas.append(p)

            return perguntas_selecionadas

        except PerguntasInsuficientesError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Erro de conexão/consulta ao buscar perguntas no Supabase: {exc}"
            ) from exc

    def salvar_partida_idempotente(self, dados_partida: dict[str, Any]) -> bool:
        """
        Persiste os dados da partida na tabela 'partidas' de forma idempotente.
        Utiliza 'upsert' com base na chave primária 'id' (UUID v4 gerado na partida)
        para garantir que reintentos nunca dupliquem o registro no banco.

        Args:
            dados_partida (dict[str, Any]): Dicionário seguindo o contrato da tabela 'partidas'.

        Returns:
            bool: True somente se o Supabase confirmar a gravação dos dados.

        Raises:
            DatabaseError: Em caso de queda de rede, timeout ou rejeição pelo banco.
        """
        try:
            resposta = (
                self.client.table("partidas")
                .upsert(dados_partida, on_conflict="id")
                .execute()
            )
            # Confirmação estrita: verifica se a resposta contém o registro salvo
            if resposta is not None and isinstance(resposta.data, list) and len(resposta.data) > 0:
                return True

            raise DatabaseError(
                "O Supabase não retornou confirmação de gravação dos dados (resposta vazia)."
            )
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Falha ao salvar partida no Supabase (UUID: {dados_partida.get('id')}): {exc}"
            ) from exc

    def salvar_ajudas(self, ajudas: list[dict[str, Any]]) -> None:
        """Persiste as ajudas da partida; reenvios não devem criar duplicatas."""
        if not ajudas:
            return
        try:
            self.client.table("ajudas_utilizadas").upsert(
                ajudas, on_conflict="partida_id,pergunta_id,tipo"
            ).execute()
        except Exception as exc:
            raise DatabaseError(f"Falha ao salvar historico de ajudas: {exc}") from exc

    def consultar_ranking_top10(self) -> list[dict[str, Any]]:
        """
        Consulta as 10 melhores partidas registradas para o JOGO_ID atual.
        Critérios de ordenação:
          1. Maior valor_ganho (decrescente)
          2. Maior número de acertos (decrescente)
          3. Menor tempo_segundos (crescente - desempate por rapidez)

        Returns:
            list[dict[str, Any]]: Lista com até 10 registros do ranking.

        Raises:
            DatabaseError: Se ocorrer falha na comunicação com o Supabase.
        """
        try:
            resposta = (
                self.client.table("partidas")
                .select(
                    "apelido, valor_ganho, acertos, tempo_segundos, "
                    "motivo_encerramento, data_hora"
                )
                .eq("jogo_id", self.config.jogo_id)
                .order("valor_ganho", desc=True)
                .order("acertos", desc=True)
                .order("tempo_segundos", desc=False)
                .limit(10)
                .execute()
            )
            return resposta.data or []
        except Exception as exc:
            raise DatabaseError(
                f"Não foi possível consultar o ranking no Supabase: {exc}"
            ) from exc
