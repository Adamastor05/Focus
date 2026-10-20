import itertools
import time
from config.tokens import GEMINI_API_KEYS


# ============================================================
# CONFIGURAÇÃO
# ============================================================

# Tempo que uma API ficará em cooldown depois de um erro 429.
# 60 segundos = 1 minuto.
COOLDOWN_429 = 60


# ============================================================
# CONTROLE DAS APIs
# ============================================================

# Rotação das APIs:
# API 1 → API 2 → API 3 → API 1 → ...
_api_cycle = itertools.cycle(range(len(GEMINI_API_KEYS)))

# Guarda até que momento cada API está em cooldown.
# Exemplo:
# {0: 1756130000.0}
#
# Significa que a API de índice 0 está indisponível
# até aquele timestamp.
_api_cooldown = {}


def proxima_api():
    """
    Retorna a próxima API disponível.

    Se uma API estiver em cooldown, ela será pulada.
    """

    quantidade_apis = len(GEMINI_API_KEYS)

    if quantidade_apis == 0:
        raise RuntimeError("Nenhuma API do Gemini foi configurada no config.py.")

    # Tenta encontrar uma API disponível.
    for _ in range(quantidade_apis):

        indice = next(_api_cycle)

        # Verifica se essa API está em cooldown.
        tempo_cooldown = _api_cooldown.get(indice, 0)

        if time.time() >= tempo_cooldown:
            return GEMINI_API_KEYS[indice]

    # Todas as APIs estão em cooldown.
    raise RuntimeError(
        "Todas as APIs do Gemini estão temporariamente indisponíveis."
    )


def marcar_api_como_indisponivel(api_key, segundos=COOLDOWN_429):
    """
    Coloca uma API em cooldown.

    Deve ser chamada quando a API retornar 429.
    """

    try:
        indice = GEMINI_API_KEYS.index(api_key)
    except ValueError:
        return

    _api_cooldown[indice] = time.time() + segundos

    print(
        f"[Gemini Manager] API {indice + 1} entrou em cooldown "
        f"por {segundos} segundos."
    )


def api_disponivel(api_key):
    """
    Verifica se uma determinada API está disponível.
    """

    try:
        indice = GEMINI_API_KEYS.index(api_key)
    except ValueError:
        return False

    return time.time() >= _api_cooldown.get(indice, 0)


def quantidade_apis():
    """
    Retorna a quantidade de APIs configuradas.
    """

    return len(GEMINI_API_KEYS)