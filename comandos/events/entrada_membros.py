import asyncio
import re
from datetime import datetime, timezone

import discord

from comandos.prefix.chat import registrar_log
from config.IDs import *


async def membro_esta_na_thread_passar_direto(membro: discord.Member):
    """
    Verifica se o ID do membro está registrado na thread
    chat_thread_passar_direto.

    Retorna:
        True  -> ID encontrado
        False -> ID não encontrado ou erro
    """

    try:
        thread = membro.guild.get_channel(chat_thread_passar_direto)

        if thread is None:
            thread = await membro.guild.fetch_channel(chat_thread_passar_direto)

        if thread is None:
            print(
                f"[PASSAR DIRETO] Não foi possível encontrar "
                f"a thread {chat_thread_passar_direto}."
            )
            return False

        id_membro = str(membro.id)

        # Procura em todas as mensagens, inclusive antigas
        async for mensagem in thread.history(limit=None):

            # Procura o ID como número isolado
            padrao = rf"(?<!\d){re.escape(id_membro)}(?!\d)"

            if re.search(padrao, mensagem.content):
                return True

        return False

    except Exception as e:
        print(
            f"[PASSAR DIRETO] Erro ao verificar "
            f"{membro} ({membro.id}): {e}"
        )
        return False


async def passar_membro_direto(membro: discord.Member):
    """
    Remove os cargos do processo de entrada e adiciona
    os cargos de membro normal.
    """

    # Cargos que devem ser removidos
    cargos_remover_ids = [
        cargo_pedir_acesso,
        cargo_ver_chat_explicacao,
        a_verificar,
        cargo_conta_suspeita,
    ]

    # Cargos que devem ser adicionados
    cargos_adicionar_ids = [
        cargo_CC,
        cargo_membro,
        conquista_a_fundacao,
        cargo_divisoria_conquistas,
        cargo_divisoria_pings,
        cargo_divisoria_caracteristicas,
        cargo_tempo,
    ]

    cargos_remover = [
        cargo
        for cargo in membro.guild.roles
        if cargo.id in cargos_remover_ids
        and cargo in membro.roles
    ]

    cargos_adicionar = [
        cargo
        for cargo in membro.guild.roles
        if cargo.id in cargos_adicionar_ids
        and cargo not in membro.roles
    ]

    # Remove os cargos de entrada
    if cargos_remover:
        await membro.remove_roles(
            *cargos_remover,
            reason="Passagem direta autorizada."
        )

    # Adiciona os cargos normais
    if cargos_adicionar:
        await membro.add_roles(
            *cargos_adicionar,
            reason="Passagem direta autorizada."
        )

    # Avisar na thread do chat_convites
    await procurar_topico_e_enviar(
        membro.guild,
        membro,
        chat_convites,
        (
            f"🚀 **Passagem direta**\n"
            f"{membro.mention} passou diretamente pelo sistema de entrada.\n"
            f"-# ID: `{membro.id}`"
        )
    )

    # Log
    await registrar_log(
        membro.guild,
        "🚀 Passagem direta",
        (
            f"**Membro:** {membro.mention}\n"
            f"**ID:** `{membro.id}`\n"
            f"**Motivo:** ID encontrado em "
            f"`chat_thread_passar_direto`."
        ),
        discord.Color.green()
    )


async def criar_ticket_entrada(membro: discord.Member):
    role = discord.utils.get(membro.guild.roles, id=cargo_ver_chat_explicacao)

    if role:
        await asyncio.sleep(2)
        await membro.remove_roles(role)

    channel = membro.guild.get_channel(chat_ticket)

    if channel is None:
        return

    # cria thread privada
    thread = await channel.create_thread(
        name=f"{membro.name} {membro.id}",
        type=discord.ChannelType.private_thread,
        invitable=False,
        auto_archive_duration=60
    )
    embed = discord.Embed(
        title="Por que você gostaria de entrar no servidor?",
        description="Pedimos que você leia as **[regras](https://discord.com/channels/1347727626088878151/1517166503584202965)**, responda a pergunta acima e aguarde até a moderação analisar se você poderá acessar o servidor. Esse sistema ajuda a proteger a comunidade contra bots e trolls.",
        color=discord.Color.yellow()
    )

    embed.set_thumbnail(url=membro.display_avatar.url)

    await thread.send(
        content=f"{membro.mention}, <@&1419489233940512828>",
        embed=embed
    )

    # add a pessoa na thread
    await asyncio.sleep(1)
    try:
        await thread.add_user(membro)
    except Exception as e:
        print(f"Erro ao adicionar usuário na thread: {e}")
        
    # Verifica a idade da conta
    conta_suspeita_id = 1457175374772568177
    cargo_suspeita = membro.guild.get_role(conta_suspeita_id)
    cargo_a_verificar = membro.guild.get_role(a_verificar)

    idade_conta = datetime.now(timezone.utc) - membro.created_at

    if idade_conta.days <= 14:
        if cargo_suspeita:
            await membro.add_roles(
                cargo_suspeita, 
                 cargo_a_verificar,
                reason="Conta criada há 14 dias ou menos.")

        await thread.send(
            f"{membro.mention} faça a verificação em <#1485807613315645571>.\n"
        )

    outros_protestantes_ids = [
    pentecostais[0],
    pentecostais[1],
    pentecostais[2],
    batista,
    presbiteriano,
    adventista,
    luterano,
    metodista,
    anglicano,
    ccb
]

    cargos_cristaos = (
        catolicos
        + [protestante, neopentecostal, outra_denominacao, ccb]
        + outros_protestantes_ids
    )

    member_roles = {role.id for role in membro.roles}

    tem_nao_cristao = nao_cristao in member_roles
    tem_catolico = any(r in member_roles for r in catolicos)
    tem_protestante = protestante in member_roles
    tem_neopentecostal = neopentecostal in member_roles
    tem_outra_denominacao = outra_denominacao in member_roles
    tem_ccb = ccb in member_roles

    qtd_outros_protestantes = sum(
        1 for cargo in outros_protestantes_ids if cargo in member_roles
    )

    perguntar_denominacao = (
        (tem_catolico and tem_protestante)
        or (tem_catolico and qtd_outros_protestantes >= 1)
        or tem_outra_denominacao
        or (qtd_outros_protestantes >= 3)
        or (tem_catolico and tem_neopentecostal)
    )

    tem_algum_cargo_cristao = any(
        cargo in member_roles for cargo in cargos_cristaos
    )

    if perguntar_denominacao:
        await thread.send(f"{membro.mention} você é de qual denominação cristã?")
    elif tem_nao_cristao or not tem_algum_cargo_cristao:
        await thread.send(f"{membro.mention} qual é a sua religião?")
# Caso contrário, não envia nada.


async def procurar_topico_e_enviar(guild, membro, chat_id, mensagem):
    canal = guild.get_channel(chat_id)

    if canal is None:
        return

    # Tópicos ativos
    for topico in canal.threads:
        if str(membro.id) in topico.name:
            await topico.send(mensagem)
            return

    # Tópicos arquivados
    try:
        async for topico in canal.archived_threads(limit=None):
            if str(membro.id) in topico.name:
                await topico.send(mensagem)
                return
    except (discord.Forbidden, discord.HTTPException):
        pass
