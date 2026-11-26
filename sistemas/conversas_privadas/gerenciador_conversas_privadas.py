from .thread_para_dm import registrar_thread_para_dm
from .dm_para_thread import registrar_dm_para_thread
from .reacoes import registrar_reacoes


def registrar(bot):
    if getattr(bot, "_conversas_privadas_registrado", False):  # evita listeners duplicados
        return
    bot._conversas_privadas_registrado = True

    registrar_thread_para_dm(bot)
    registrar_dm_para_thread(bot)
    registrar_reacoes(bot)