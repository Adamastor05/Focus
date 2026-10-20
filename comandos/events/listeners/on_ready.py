
import asyncio

from comandos.events.agendar_mensagens import iniciar_agendador
from comandos.events.aparicoes_diarias import iniciar_tarefa_aparicoes_diarias
from comandos.events.prodigos import iniciar_tarefa_prodigos
from comandos.events.sapphire_thread import verificar_thread_sapphire
from config.IDs import chat_conversas, chat_logs, chat_thread_agendar_msgs
from config.versao import VERSAO_ATUAL


agendador_mensagens_task = None
aparicoes_diarias_task = None


def registrar_evento_on_ready(bot):
    @bot.event
    async def on_ready():

        global agendador_mensagens_task

        await bot.tree.sync()

        print(f"Logado como {bot.user}")

        channel = bot.get_channel(chat_logs)

        if channel is not None:
            await channel.send(
                f"""🟢 "E foi feito alma vivente."
-# 📁 `Focus {VERSAO_ATUAL}`"""
            )

        await verificar_thread_sapphire(bot)

        # ============================================================
        # AGENDADOR DE MENSAGENS
        # ============================================================

        if (
            agendador_mensagens_task is None
            or agendador_mensagens_task.done()
        ):

            agendador_mensagens_task = asyncio.create_task(
                iniciar_agendador(
                    bot,
                    chat_thread_agendar_msgs,
                    chat_conversas,
                    chat_logs
                )
            )

        #region APARIÇÕES DIÁRIAS ------------

        global aparicoes_diarias_task
        if (
            aparicoes_diarias_task is None
            or aparicoes_diarias_task.done()
        ):
            aparicoes_diarias_task = iniciar_tarefa_aparicoes_diarias(
                bot
            )
        #endregion

        #region Pródigos
        iniciar_tarefa_prodigos(bot)