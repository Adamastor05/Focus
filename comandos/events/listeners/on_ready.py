import asyncio

# --- eventos / tarefas ---
from sistemas.agendamentos.gerenciador_agendamentos import rodar_agendamentos
from comandos.events.aparicoes_diarias import iniciar_tarefa_aparicoes_diarias
from comandos.events.apagar_sapphire_thread import verificar_thread_sapphire
from comandos.events.prodigos import iniciar_tarefa_prodigos

# --- sistema de acesso ao servidor ---
from sistemas.acesso.acesso_ao_servidor import registrar as registrar_acesso
from sistemas.acesso.botao_acesso import registrar_botao_acesso
from sistemas.acesso.forcar_acesso import registrar_forcar_acesso

# --- config ---
from config.IDs import chat_logs
from config.versao import VERSAO_ATUAL


agendador_mensagens_task = None
aparicoes_diarias_task = None
acesso_registrado = False


def registrar_evento_on_ready(bot):
    @bot.event
    async def on_ready():

        global agendador_mensagens_task
        global aparicoes_diarias_task
        global acesso_registrado

        # ============================================================
        # AGENDAMENTOS
        # Iniciado logo no começo para que um erro em qualquer coisa
        # abaixo não impeça o sistema de ligar. (on_ready pode rodar
        # mais de uma vez, por isso a trava com a task.)
        # ============================================================

        if (
            agendador_mensagens_task is None
            or agendador_mensagens_task.done()
        ):
            agendador_mensagens_task = asyncio.create_task(
                rodar_agendamentos(bot)
            )

        # ============================================================
        # SISTEMA DE ACESSO (registrar ANTES do sync;
        # on_ready pode rodar mais de uma vez, por isso a trava)
        # ============================================================

        if not acesso_registrado:
            acesso_registrado = True
            registrar_acesso(bot)              # aviso de mensagens nas threads de acolhimento
            await registrar_botao_acesso(bot)  # /acesso_servidor_focus + botão persistente
            registrar_forcar_acesso(bot)       # /forçar_acesso

        await bot.tree.sync()

        print(f"Logado como {bot.user}")

        channel = bot.get_channel(chat_logs)

        if channel is not None:
            await channel.send(
                f"""🟢 "E foi feito alma vivente." — Gn 2.7b
-# 📁** `Focus {VERSAO_ATUAL}` **"""
            )

        await verificar_thread_sapphire(bot)

        #region APARIÇÕES DIÁRIAS ------------

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
        #endregion