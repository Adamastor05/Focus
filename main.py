import discord
from discord.ext import commands
from discord.utils import get
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
import asyncio
import re
import time
from discord.ext import tasks
from zoneinfo import ZoneInfo
from datetime import time
from config.tokens import TOKEN
from config.IDs import *





bot = commands.Bot(command_prefix=";", intents=intents, help_command=None)


#region ------- 🗂️ Em outras pastas...
#region---------------------------- prefix
from comandos.prefix.basicos import registrar_comandos_basicos
registrar_comandos_basicos(bot)
#endregion

#region---------------------------- slash
#region 📞👥cargo_call
from comandos.slash.cargo_call import registrar_comando_cargo_call
registrar_comando_cargo_call(
    bot,
    valentes,
    chat_logs
)
#endregion
#region 📴desligar_focus
from comandos.slash.desligar_focus import registrar_comando_desligar_focus
registrar_comando_desligar_focus(
    bot,
    chat_logs,
    CARGO_FOCUS_ADM,
    CARGO_ADM
)
#endregion
#region 👥👥adicionar_cargo_em_massa
from comandos.slash.adicionar_cargo_em_massa import (
    registrar_comando_adicionar_cargo_em_massa
)
registrar_comando_adicionar_cargo_em_massa(
    bot,
    CARGO_FOCUS_ADM,
    CARGO_ADM,
    chat_logs
)
#endregion
#region ⭐mensagem do dia (ping)
from comandos.slash.mensagem_do_dia import (
    registrar_comando_mensagem_do_dia
)
registrar_comando_mensagem_do_dia(
    bot,
    CARGO_FOCUS_ADM,
    CARGO_ADM,
    chat_mensagem_do_dia,
    chat_logs
)
#endregion
#region mensagem_pv
from comandos.slash.mensagem_pv import (
    registrar_comando_mensagem_pv
)
registrar_comando_mensagem_pv(
    CARGO_MODERADOR=CARGO_MODERADOR,
    bot=bot,
    chat_logs=chat_logs
)
#endregion
#region Limpar DMs
from comandos.slash.limpar_dm import registrar_comando_limpar_dm
registrar_comando_limpar_dm(
    bot,
    CARGO_MODERADOR,
)
#endregion
#region Remover cargo de todos
from comandos.slash.remove_role_all import registrar_comando_remove_role_all
registrar_comando_remove_role_all(
    bot,
    CARGO_ADM,
)
#endregion
#region Transferir cargos em massa
from comandos.slash.transferir_cargo_em_massa import (
    registrar_comando_transferir_cargo_em_massa,
)
registrar_comando_transferir_cargo_em_massa(
    bot,
    CARGO_ADM,
    chat_logs,
)
#endregion
#region Cargo para membros ativos
from comandos.slash.adicionar_cargo_3d import (
    registrar_comando_adicionar_cargo_3d,
)
registrar_comando_adicionar_cargo_3d(
    bot,
    CARGO_ADM,
    chat_logs,
)
#endregion
#region Lembretes de pedido de acesso
from comandos.slash.relembrar_pedir_acesso import (
    registrar_comando_relembrar_pedir_acesso,
)
registrar_comando_relembrar_pedir_acesso(
    bot,
    CARGO_ADM,
    cargo_pedir_acesso,
    chat_ticket,
    chat_logs,
)
#endregion
#region Resumir conversa com Gemini
from comandos.slash.resumir_com_gemini import (
    registrar_comando_resumir_com_gemini,
)
registrar_comando_resumir_com_gemini(
    bot,
    valentes,
)
#endregion
#region Cor do cargo de booster
from comandos.slash.cor import registrar_comando_cor
registrar_comando_cor(
    bot,
    cargo_booster,
    chat_logs_thread_boosters,
)
#endregion
#region Ranking de Mensagem do Dia
from comandos.slash.ranking_mdd import registrar_comando_ranking_mdd
registrar_comando_ranking_mdd(
    bot,
    chat_mensagem_do_dia,
)
#endregion
#region Cores do Destaque do Dia
from comandos.slash.cor_destaque_do_dia import (
    registrar_comando_cor_destaque_do_dia,
)
registrar_comando_cor_destaque_do_dia(
    bot,
    cargo_destaque_do_dia,
    CARGO_MODERADOR,
)
#endregion
#region Alterar apelido
from comandos.slash.alterar_apelido import (
    registrar_comando_alterar_apelido,
)
registrar_comando_alterar_apelido(
    bot,
    cargo_destaque_do_dia,
    cargo_booster,
    chat_logs_threads_apelidos_DDD,
)
#endregion

#region---------------------------- events
#region 📅agendar_mensagens
#endregion
#region 🔵sapphire threads, apagar
from comandos.events.apagar_sapphire_thread import (
    on_thread_create,
    verificar_thread_sapphire
)
bot.add_listener(on_thread_create, "on_thread_create")
#endregion
#region 👤 aparicoes diarias
from comandos.events.aparicoes_diarias import (
    registrar_aparicoes_diarias,
)

registrar_aparicoes_diarias(
    bot,
    CARGO_ADM,
    CARGO_FOCUS_ADM
)

#endregion
#region Pródigos
from comandos.events.prodigos import (
    registrar_comando_prodigos,
)

registrar_comando_prodigos(
    bot,
    CARGO_ADM,
    CARGO_FOCUS_ADM,
)
#endregion
#endregion
#endregion
#endregion


#region -------------- ;chat
from comandos.prefix.chat import (
    registrar_comando_prefix_chat,
)
registrar_comando_prefix_chat(bot)
#endregion

#region comando ;r ou ;registro
from comandos.prefix.registro import registrar_comando_prefix_registro
registrar_comando_prefix_registro(
    bot,
    CARGO_MODERADOR,
    chat_registro,
)
#endregion


#region comando ;rm ou ;registrom
from comandos.prefix.registrom import registrar_comando_prefix_registrom
registrar_comando_prefix_registrom(
    bot,
    CARGO_MODERADOR,
    chat_registro,
    asyncio,
)
#endregion

#region comando ;m ou ;mensagem
from comandos.prefix.mensagem import registrar_comando_mensagem
registrar_comando_mensagem(
    bot,
    discord,
    re,
    CARGO_MODERADOR,
    cargo_recepcionista,
    chat_logs,
)
#endregion


#region -------------- /salvar_ids_cargo
from comandos.slash.salvar_ids_cargo import registrar_comando_salvar_ids_cargo
registrar_comando_salvar_ids_cargo(
    bot,
    CARGO_ADM,
    chat_logs,
)
#endregion


#region -------------- criar convite
from comandos.slash.criar_convite import registrar_comando_criar_convite
registrar_comando_criar_convite(
    bot,
    CARGO_ADM
)
#endregion

import comandos.slash.analisar_foto_perfil
comandos.slash.analisar_foto_perfil.setup(bot)

#region -------------- Registros de eventos
# aqui ficava o on_ready

from comandos.events.listeners.on_thread_create import registrar_evento_on_thread_create
registrar_evento_on_thread_create(
    bot,
    chat_logs
)


from comandos.events.listeners.on_member_join import registrar_evento_on_member_join
registrar_evento_on_member_join(bot)



#endregion


#region Manualmente:
from comandos.events.entrada_membros import criar_ticket_entrada
from comandos.slash.criar_ticket import registrar_comando_criar_ticket
registrar_comando_criar_ticket(
    bot,
    CARGO_MODERADOR,
    criar_ticket_entrada,
)
#endregion

from comandos.events.listeners.on_member_update import (
    registrar_evento_on_member_update,
)
registrar_evento_on_member_update(bot)

#from comandos.events.listeners.on_user_update import registrar_evento_on_user_update
#registrar_evento_on_user_update(bot)
from comandos.events.listeners.on_member_remove import (
    registrar_evento_on_member_remove,
)
registrar_evento_on_member_remove(bot)

#region -------------- /verificar_a_verificar
from comandos.slash.verificar_a_verificar import (
    registrar_comando_verificar_a_verificar,
)
registrar_comando_verificar_a_verificar(
    bot,
    CARGO_MODERADOR,
    a_verificar,
    cargo_conta_suspeita,
    cargo_pedir_acesso,
)
#endregion

from comandos.context.motivo import registrar_comando_motivo
registrar_comando_motivo(bot)



from comandos.events.listeners.on_command_error import (
    registrar_evento_on_command_error,
)
registrar_evento_on_command_error(bot)

from comandos.events.listeners.on_message import registrar_evento_on_message
registrar_evento_on_message(bot)


from comandos.events.listeners.on_voice_state_update import (
    registrar_evento_on_voice_state_update,
)
registrar_evento_on_voice_state_update(bot)

#region Marcar @ver_chat_explicação automaticamente
@tasks.loop(time=time(hour=20, minute=0, tzinfo=ZoneInfo("America/Sao_Paulo")))
async def lembrete_chat_explicacao():

    canal = bot.get_channel(chat_ticket_apolo)

    if canal is None:
        return

    mensagem = await canal.send(
        f"Crie um ticket <@&{cargo_ver_chat_explicacao}>"
    )

    await asyncio.sleep(10)

    try:
        await mensagem.delete()
    except discord.NotFound:
        pass
#endregion

import comandos.events.contador_emojis
comandos.events.contador_emojis.registrar(bot)

import comandos.events.booster_logs
comandos.events.booster_logs.setup(bot)

import comandos.events.analisar_mdd
comandos.events.analisar_mdd.setup(bot)

import sistemas.manipular_cargos.slash.salvar_cargos_thread
sistemas.manipular_cargos.slash.salvar_cargos_thread.setup(bot)
# e lembre de dar o sync da árvore (await bot.tree.sync()) depois de registrar

from comandos.events.listeners.on_ready import registrar_evento_on_ready
registrar_evento_on_ready(bot)

from comandos.slash.resumir_conversa import registrar_comando_resumir_conversa
registrar_comando_resumir_conversa(bot)

from sistemas.acesso.acesso_ao_servidor import registrar as registrar_acesso
from sistemas.acesso.botao_acesso import registrar_botao_acesso
from sistemas.acesso.acesso_verificar import acesso_ao_verificar
acesso_ao_verificar(bot)

from sistemas.agendamentos.gerenciador_agendamentos import rodar_agendamentos

from sistemas.apresentacoes.ping_acolhimento import registrar_evento_on_thread_create
registrar_evento_on_thread_create(bot)

from sistemas.apresentacoes.apagar_thread_acolhimento import registrar_evento_atualizar_agendamento
registrar_evento_atualizar_agendamento(bot)

from sistemas.entrada.espelhar_ticket import espelhar_ticket_convites
espelhar_ticket_convites(bot)

#from sistemas.conversas_privadas.gerenciador_conversas_privadas import registrar as registrar_conversas_privadas
#registrar_conversas_privadas(bot)

from sistemas.analise_pfp.perfil_listeners import registrar_listeners_perfil
from sistemas.analise_pfp.perfil_fechar import registrar_fechar_perfil
registrar_listeners_perfil(bot)
registrar_fechar_perfil(bot)

bot.run(TOKEN)