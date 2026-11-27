"""
Remove o CARGO_TEMPO de todos às 05:00 (Brasília), parando só quando remover de todos.

Uso no main:
    from sistemas.timed_roles.events import remover_cargo_tempo
    remover_cargo_tempo.setup(bot)
"""
from .agendador import agendar_diario, cargos_encontrados, remover_cargo_de_membros

# ===================== CONFIGURAÇÃO =====================
HORA, MINUTO = 5, 0
ORDEM_REVERSA = True   # começa do fim da lista p/ não competir com o outro bot
MAX_PASSADAS = 5       # quantas vezes tenta de novo se sobrar alguém
# ========================================================


async def executar(bot):
    for guild, cargo in cargos_encontrados(bot):
        await remover_cargo_de_membros(
            guild, cargo,
            filtro=lambda m: True,
            nome="remover_cargo",
            ordem_reversa=ORDEM_REVERSA,
            max_passadas=MAX_PASSADAS,
        )


def setup(bot):
    agendar_diario(bot, "remover_cargo", HORA, MINUTO, executar)