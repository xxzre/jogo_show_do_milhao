"""
Módulo de configuração do sistema.
Responsável por carregar variáveis de ambiente do arquivo .env e validar
as credenciais obrigatórias para conexão com o Supabase.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Carrega as variáveis definidas no arquivo .env (se existir)
load_dotenv()


class ConfigError(Exception):
    """Exceção lançada quando há erro ou ausência nas variáveis de ambiente."""
    pass


@dataclass(frozen=True)
class AppConfig:
    """Estrutura imutável de configuração da aplicação."""
    supabase_url: str
    supabase_key: str
    jogo_id: int | str


def carregar_configuracao() -> AppConfig:
    """
    Lê e valida as variáveis de ambiente necessárias para execução do jogo.

    Returns:
        AppConfig: Objeto contendo SUPABASE_URL, SUPABASE_KEY e JOGO_ID validados.

    Raises:
        ConfigError: Se alguma variável obrigatória não estiver configurada ou for inválida.
    """
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()
    jogo_id_raw = os.getenv("JOGO_ID", "").strip()

    campos_faltantes: list[str] = []

    if not supabase_url or supabase_url == "https://seu-projeto.supabase.co":
        campos_faltantes.append("SUPABASE_URL")
    if not supabase_key or supabase_key == "sua-anon-key-aqui":
        campos_faltantes.append("SUPABASE_KEY")
    if not jogo_id_raw:
        campos_faltantes.append("JOGO_ID")

    if campos_faltantes:
        raise ConfigError(
            f"Variáveis de ambiente ausentes ou não configuradas no arquivo .env: "
            f"{', '.join(campos_faltantes)}.\n"
            f"Dica: Copie o arquivo '.env.example' para '.env' e preencha com os dados do Supabase."
        )

    if not (supabase_url.startswith("http://") or supabase_url.startswith("https://")):
        raise ConfigError(
            f"SUPABASE_URL inválida ('{supabase_url}'). Deve iniciar com http:// ou https://."
        )

    # Converte JOGO_ID para inteiro caso seja numérico (ex: ID serial no banco),
    # ou mantém como string caso a equipe utilize UUID na tabela 'jogos'.
    jogo_id: int | str = int(jogo_id_raw) if jogo_id_raw.isdigit() else jogo_id_raw

    return AppConfig(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        jogo_id=jogo_id,
    )
