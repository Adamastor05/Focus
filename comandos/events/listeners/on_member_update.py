import asyncio

import discord

from comandos.events.entrada_membros import (
    criar_ticket_entrada,
    membro_esta_na_thread_passar_direto,
    passar_membro_direto,
    procurar_topico_e_enviar,
)
from comandos.events.destaque_do_dia import verificar_destaque_do_dia
from comandos.events.topico_privado_automatico import (
    criar_topico_privado_automatico,
)
from comandos.prefix.chat import obter_ou_criar_chat
from config.IDs import (
    cargo_destaque_do_dia,
    cargo_pedir_acesso,
    cargo_verificado,
    chat_convites,
    chat_ticket,
    chat_thread_ddd_logs,
)


def registrar_evento_on_member_update(bot):
    @bot.event
    async def on_member_update(before: discord.Member, after: discord.Member):
        # ---------------------------------- Ticket de entrada
        await asyncio.sleep(2)
        if before.pending and not after.pending:

            passou_direto = await membro_esta_na_thread_passar_direto(after)

            if passou_direto:
                await passar_membro_direto(after)
            else:
                await criar_ticket_entrada(after)

        # ------------------------------ cargo verificado e pedir_acesso
        # ---------------------------------- Alterações de cargos

        cargos_antes = {cargo.id for cargo in before.roles}
        cargos_depois = {cargo.id for cargo in after.roles}

        # Ganhou o cargo verificado
        if (
            cargo_verificado in cargos_depois
            and cargo_verificado not in cargos_antes
        ):
            mensagem = f"""<@{after.id}> se verificou.
-# <@&1419489233940512828>
        """

            await procurar_topico_e_enviar(
                after.guild,
                after,
                chat_convites,
                mensagem
            )

            await procurar_topico_e_enviar(
                after.guild,
                after,
                chat_ticket,
                mensagem
            )

        # Perdeu o cargo pedir acesso
        if (
            cargo_pedir_acesso in cargos_antes
            and cargo_pedir_acesso not in cargos_depois
        ):

            asyncio.create_task(
                criar_topico_privado_automatico(
                after.guild,
                after,
                obter_ou_criar_chat
            )
            )

            mensagem = f"<@{after.id}> acessou o servidor."

            await procurar_topico_e_enviar(
                after.guild,
                after,
                chat_convites,
                mensagem
            )

            await procurar_topico_e_enviar(
                after.guild,
                after,
                chat_ticket,
                mensagem
            )

        await verificar_destaque_do_dia(
            bot,
            before,
            after,
            cargo_destaque_do_dia,
            chat_thread_ddd_logs
        )
