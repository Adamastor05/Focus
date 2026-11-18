import asyncio

from comandos.events.agendar_mensagens import iniciar_agendador
from comandos.events.aparicoes_diarias import iniciar_tarefa_aparicoes_diarias
from comandos.events.prodigos import iniciar_tarefa_prodigos
from comandos.events.apagar_sapphire_thread import verificar_thread_sapphire
from sistemas.entrada.acesso_ao_servidor import registrar as registrar_acesso   # v3.2
from sistemas.entrada.botao_acesso import registrar_botao_acesso                 # v3.2
from config.IDs import chat_conversas, chat_logs, chat_thread_agendar_msgs
from config.versao import VERSAO_ATUAL


agendador_mensagens_task = None
aparicoes_diarias_task = None
acesso_registrado = False                                                      # v3.2


def registrar_evento_on_ready(bot):
    @bot.event
    async def on_ready():

        global agendador_mensagens_task
        global acesso_registrado                                               # v3.2

        # NOVO: registrar antes do sync (on_ready pode rodar mais de uma vez)
        if not acesso_registrado:
            acesso_registrado = True
            registrar_acesso(bot)
            await registrar_botao_acesso(bot)

        await bot.tree.sync()

        print(f"Logado como {bot.user}")

        channel = bot.get_channel(chat_logs)

        if channel is not None:
            await channel.send(
                f"""🟢 "E foi feito alma vivente." — Gn 2.7b
-# 📁** `Focus {VERSAO_ATUAL}` **"""
            )

        await verificar_thread_sapphire(bot)

        # AGENDADOR DE MENSAGENS
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