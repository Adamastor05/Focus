"""
Remove o CARGO_TEMPO de todos os BOTS às 00:15 (Brasília).

Uso no main:
    from sistemas.timed_roles.events import remover_cargo_tempo_bots
    remover_cargo_tempo_bots.setup(bot)
"""
from .agendador import agendar_diario, cargos_encontrados, remover_cargo_de_membros

# ===================== CONFIGURAÇÃO =====================
HORA, MINUTO = 0, 15
MAX_PASSADAS = 5
# ========================================================


async def executar(bot):
    for guild, cargo in cargos_encontrados(bot):
        await remover_cargo_de_membros(
            guild, cargo,
            filtro=lambda m: m.bot,
            nome="remover_cargo_bots",
            ordem_reversa=False,
            max_passadas=MAX_PASSADAS,
        )


def setup(bot):
    agendar_diario(bot, "remover_cargo_bots", HORA, MINUTO, executar)