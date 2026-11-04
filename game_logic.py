"""
Módulo de regras de negócio e máquina de estados do jogo Show do Milhão.
Controla a tabela de prêmios substitutivos, validação de entradas no terminal,
cronometragem exata com time.perf_counter() e geração do payload da partida.
"""

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# Tabela oficial de prêmios (Não acumulativos / Substitutivos)
# Índice 0 = 1ª pergunta, Índice 8 = 9ª pergunta (Pergunta do Milhão)
TABELA_PREMIOS: tuple[float, ...] = (
    1_000.0,      # 1ª (Fácil)
    5_000.0,      # 2ª (Fácil)
    10_000.0,     # 3ª (Fácil)
    25_000.0,     # 4ª (Média)
    50_000.0,     # 5ª (Média)
    100_000.0,    # 6ª (Média)
    200_000.0,    # 7ª (Difícil)
    500_000.0,    # 8ª (Difícil)
    1_000_000.0,  # 9ª (Difícil)
)

ROTULO_DIFICULDADE: dict[str, str] = {
    "facil": "FÁCIL",
    "media": "MÉDIA",
    "dificil": "DIFÍCIL",
}


def formatar_moeda(valor: float) -> str:
    """
    Formata um valor numérico para o padrão monetário brasileiro (ex: R$ 1.000,00).
    """
    texto = f"{valor:,.2f}"
    # Converte separadores do padrão americano (1,000.00) para brasileiro (1.000,00)
    texto_br = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto_br}"


def solicitar_apelido() -> str:
    """
    Solicita o apelido do jogador com validação em loop (não permite vazio).
    """
    while True:
        try:
            apelido = input("\nDigite seu apelido para iniciar a partida: ").strip()
        except EOFError:
            apelido = ""

        if apelido:
            return apelido

        print("[!] Erro: O apelido é obrigatório e não pode ficar em branco. Tente novamente.")


@dataclass
class ResultadoPartida:
    """Representa o estado final consolidado de uma partida encerrada."""
    id: str
    jogo_id: int | str
    apelido: str
    valor_ganho: float
    tempo_segundos: float
    acertos: int
    motivo_encerramento: str  # 'vitoria', 'erro' ou 'desistencia'
    data_hora: str

    def para_dicionario(self) -> dict[str, Any]:
        """Converte o resultado exatamente para o contrato da tabela 'partidas' no Supabase."""
        return {
            "id": self.id,
            "jogo_id": self.jogo_id,
            "apelido": self.apelido,
            "valor_ganho": float(self.valor_ganho),
            "tempo_segundos": round(float(self.tempo_segundos), 2),
            "acertos": int(self.acertos),
            "motivo_encerramento": self.motivo_encerramento,
            "data_hora": self.data_hora,
        }


class PartidaShowDoMilhao:
    """
    Máquina de estados de uma partida do Show do Milhão.
    Garante geração prévia de UUID v4, medição isolada de tempo e regras de premiação.
    """

    def __init__(
        self,
        jogo_id: int | str,
        apelido: str,
        perguntas: list[dict[str, Any]],
    ) -> None:
        if len(perguntas) != 9:
            raise ValueError("Uma partida requer exatamente 9 perguntas pré-selecionadas.")

        # Gera o UUID v4 no início da partida (antes de qualquer tentativa de persistência)
        self.partida_id: str = str(uuid.uuid4())
        self.jogo_id: int | str = jogo_id
        self.apelido: str = apelido
        self.perguntas: list[dict[str, Any]] = perguntas

        self.acertos: int = 0
        self.valor_ganho: float = 0.0
        self.motivo_encerramento: str = ""
        self.tempo_segundos: float = 0.0

    def _exibir_pergunta(self, indice: int, pergunta: dict[str, Any]) -> None:
        """Renderiza o cabeçalho de premiação, o enunciado e as 4 alternativas."""
        numero_questao = indice + 1
        dificuldade_raw = str(pergunta.get("dificuldade", "")).lower()
        dificuldade_str = ROTULO_DIFICULDADE.get(dificuldade_raw, dificuldade_raw.upper())
        premio_atual = TABELA_PREMIOS[indice]

        print("\n" + "=" * 72)
        print(
            f" PERGUNTA {numero_questao}/9  |  Nível: {dificuldade_str}  |  "
            f"Valendo: {formatar_moeda(premio_atual)}"
        )
        print(
            f" Jogador: {self.apelido}  |  "
            f"Prêmio Garantido Atual: {formatar_moeda(self.valor_ganho)}"
        )
        print("=" * 72)
        print(f"\n{pergunta['enunciado']}\n")
        print(f"  [A] {pergunta['alternativa_a']}")
        print(f"  [B] {pergunta['alternativa_b']}")
        print(f"  [C] {pergunta['alternativa_c']}")
        print(f"  [D] {pergunta['alternativa_d']}")
        print("-" * 72)
        print("  [P] Parar / Desistir e levar o prêmio atual")
        print("-" * 72)

    def _ler_decisao_jogador(self, indice: int, pergunta: dict[str, Any]) -> str:
        """
        Solicita a escolha do jogador em loop defensivo.
        Se a entrada for inválida, exibe erro e repete a pergunta sem encerrar o jogo.
        """
        opcoes_validas = {"A", "B", "C", "D", "P", "PARAR", "DESISTIR"}

        while True:
            self._exibir_pergunta(indice, pergunta)
            try:
                entrada = input("Sua escolha (A, B, C, D ou P para parar): ").strip().upper()
            except EOFError:
                entrada = ""

            if entrada in opcoes_validas:
                if entrada in {"P", "PARAR", "DESISTIR"}:
                    return "P"
                return entrada

            print(
                "\n[!] Entrada inválida! Digite apenas A, B, C, D para responder "
                "ou P para desistir/parar. A pergunta será exibida novamente."
            )

    def executar(self) -> ResultadoPartida:
        """
        Executa o fluxo completo das 9 perguntas da partida.
        O cronômetro (time.perf_counter) inicia exatamente quando a 1ª pergunta é exibida
        e para imediatamente no encerramento da partida.
        """
        print("\n" + "*" * 72)
        print(f" PREPARADO(A), {self.apelido.upper()}? VAI COMEÇAR O SHOW DO MILHÃO!")
        print(f" ID da Partida (UUID): {self.partida_id}")
        print("*" * 72)

        # Início exato do cronômetro ao exibir a primeira pergunta
        inicio_cronometro = time.perf_counter()

        try:
            for indice, pergunta in enumerate(self.perguntas):
                escolha = self._ler_decisao_jogador(indice, pergunta)

                # Caso 1: Jogador decidiu parar/desistir
                if escolha == "P":
                    self.motivo_encerramento = "desistencia"
                    print(
                        f"\n[!] Você escolheu PARAR! "
                        f"Você mantém o prêmio acumulado de {formatar_moeda(self.valor_ganho)}."
                    )
                    break

                correta = str(pergunta["correta"]).strip().upper()

                # Caso 2: Jogador acertou a resposta
                if escolha == correta:
                    self.acertos += 1
                    # Prêmio substitutivo (não acumulativo): assume o valor da pergunta acertada
                    self.valor_ganho = TABELA_PREMIOS[indice]
                    print(
                        f"\n[✓] CERTA RESPOSTA! "
                        f"Seu prêmio agora é de {formatar_moeda(self.valor_ganho)}!"
                    )

                    if self.acertos == 9:
                        self.motivo_encerramento = "vitoria"
                        print("\n" + "#" * 72)
                        print(" PARABÉNS! VOCÊ ACERTOU TODAS AS 9 PERGUNTAS E GANHOU 1 MILHÃO DE REAIS!")
                        print("#" * 72)
                        break

                # Caso 3: Jogador errou a resposta
                else:
                    self.motivo_encerramento = "erro"
                    # Regra: se errar na 1ª pergunta, valor_ganho já é R$ 0,00.
                    # Se errar após acertos, mantém o valor da última pergunta acertada.
                    print(
                        f"\n[X] QUE PENA, VOCÊ ERROU! A alternativa correta era [{correta}]."
                    )
                    print(
                        f"    Você encerra a partida levando {formatar_moeda(self.valor_ganho)}."
                    )
                    break

        except KeyboardInterrupt:
            # Tratamento defensivo caso o usuário pressione Ctrl+C durante a partida
            self.motivo_encerramento = "desistencia"
            print(
                f"\n\n[!] Partida interrompida pelo usuário (tratada como desistência). "
                f"Prêmio mantido: {formatar_moeda(self.valor_ganho)}."
            )

        # Fim exato do cronômetro imediatamente no encerramento da partida
        fim_cronometro = time.perf_counter()
        self.tempo_segundos = round(fim_cronometro - inicio_cronometro, 2)
        data_hora_iso = datetime.now(timezone.utc).isoformat()

        resultado = ResultadoPartida(
            id=self.partida_id,
            jogo_id=self.jogo_id,
            apelido=self.apelido,
            valor_ganho=self.valor_ganho,
            tempo_segundos=self.tempo_segundos,
            acertos=self.acertos,
            motivo_encerramento=self.motivo_encerramento,
            data_hora=data_hora_iso,
        )

        self._exibir_resumo_final(resultado)
        return resultado

    @staticmethod
    def _exibir_resumo_final(resultado: ResultadoPartida) -> None:
        """Exibe o resumo estatístico da partida antes da sincronização com o banco."""
        mapa_motivo = {
            "vitoria": "Vitória (9 acertos - R$ 1.000.000,00!)",
            "erro": "Erro de resposta",
            "desistencia": "Desistência / Parada voluntária",
        }
        motivo_legivel = mapa_motivo.get(
            resultado.motivo_encerramento, resultado.motivo_encerramento
        )

        print("\n" + "=" * 72)
        print("                       RESUMO FINAL DA PARTIDA")
        print("=" * 72)
        print(f"  ID da Partida (UUID) : {resultado.id}")
        print(f"  Jogador (Apelido)    : {resultado.apelido}")
        print(f"  Acertos              : {resultado.acertos} de 9")
        print(f"  Motivo Encerramento  : {motivo_legivel}")
        print(f"  Prêmio Final         : {formatar_moeda(resultado.valor_ganho)}")
        print(f"  Tempo Total de Jogo  : {resultado.tempo_segundos:.2f} segundos")
        print("=" * 72)
