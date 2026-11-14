import asyncio
import re

import discord
from discord import app_commands

from config.IDs import CARGO_ADM, CARGO_FOCUS_ADM, CHAT_LOGS_COMPOSTO

CARGOS_PERMITIDOS = {CARGO_ADM, CARGO_FOCUS_ADM}
REGEX_ID = re.compile(r"\d{15,20}")

# Evita que duas execuções mexam na mesma thread ao mesmo tempo
_locks: dict[int, asyncio.Lock] = {}


async def _resolver_thread(bot, texto: str):
    """Aceita o id da thread, menção (<#id>) ou link. Pode ser de qualquer servidor em que o bot esteja."""
    achado = re.findall(r"\d{15,25}", texto)
    if not achado:
        return None
    thread_id = int(achado[-1])

    canal = bot.get_channel(thread_id)
    if canal is None:
        try:
            canal = await bot.fetch_channel(thread_id)  # pega até thread arquivada
        except (discord.NotFound, discord.Forbidden, discord.HTTPException, discord.InvalidData):
            return None
    return canal if isinstance(canal, discord.Thread) else None

def _dividir_ids(ids, limite=1800):
    """Divide uma lista de ids em blocos que cabem numa mensagem."""
    blocos, atual = [], ""
    for i in ids:
        linha = f"{i}\n"
        if len(atual) + len(linha) > limite:
            blocos.append(atual)
            atual = ""
        atual += linha
    if atual:
        blocos.append(atual)
    return blocos


async def _enviar_logs(bot, embed: discord.Embed, listas: list[tuple[str, list[int]]]):
    """Envia o resumo + as listas de ids em todos os chats de CHAT_LOGS_COMPOSTO."""
    for chat_id in CHAT_LOGS_COMPOSTO:
        canal = bot.get_channel(chat_id)
        if canal is None:
            try:
                canal = await bot.fetch_channel(chat_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                continue
        try:
            await canal.send(embed=embed)
            for titulo, ids in listas:
                if not ids:
                    continue
                for n, bloco in enumerate(_dividir_ids(ids), start=1):
                    sufixo = f" ({n})" if n > 1 else ""
                    await canal.send(f"**{titulo}{sufixo}**\n```\n{bloco}```")
        except discord.HTTPException:
            continue


def setup(bot):
    @bot.tree.command(
        name="salvar_cargos_thread",
        description="Salva na thread o id de todas as pessoas que possuem um cargo.",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        cargo="Cargo cujos membros serão salvos",
        thread="Thread (pode ser o id) onde os ids serão enviados",
        modo="Multidirecional apaga ids de quem perdeu o cargo; adicionar apenas não apaga",
    )
    @app_commands.choices(
        modo=[
            app_commands.Choice(name="Multidirecional", value="multidirecional"),
            app_commands.Choice(name="Adicionar apenas", value="adicionar"),
        ]
    )
    async def salvar_cargos_thread(
        interaction: discord.Interaction,
        cargo: discord.Role,
        thread: str,
        modo: app_commands.Choice[str],
    ):
        # ---------- permissão ----------
        ids_do_autor = {r.id for r in getattr(interaction.user, "roles", [])}
        if not ids_do_autor & CARGOS_PERMITIDOS:
            return await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild

        # ---------- thread ----------
        canal_thread = await _resolver_thread(bot, thread)
        if canal_thread is None:
            return await interaction.followup.send(
                "❌ Não encontrei essa thread. Confira o id e se eu tenho acesso a ela.",
                ephemeral=True,
            )

        lock = _locks.setdefault(canal_thread.id, asyncio.Lock())
        if lock.locked():
            return await interaction.followup.send(
                "⏳ Já existe uma execução em andamento nessa thread. Aguarde terminar.",
                ephemeral=True,
            )

        async with lock:
            # ---------- membros com o cargo ----------
            if not guild.chunked:
                await guild.chunk()
            ids_com_cargo = {m.id for m in cargo.members}

            # ---------- ids que já estão na thread ----------
            existentes: dict[int, list[discord.Message]] = {}
            try:
                async for msg in canal_thread.history(limit=None, oldest_first=True):
                    conteudo = msg.content.strip()
                    if REGEX_ID.fullmatch(conteudo):
                        existentes.setdefault(int(conteudo), []).append(msg)
            except discord.Forbidden:
                return await interaction.followup.send(
                    "❌ Não tenho permissão para ler o histórico dessa thread.",
                    ephemeral=True,
                )

            faltando = sorted(ids_com_cargo - existentes.keys())
            sem_cargo = sorted(uid for uid in existentes if uid not in ids_com_cargo)

            # ---------- adiciona os que faltam ----------
            adicionados, falha_envio = [], []
            for uid in faltando:
                try:
                    await canal_thread.send(str(uid))
                    adicionados.append(uid)
                except discord.HTTPException:
                    falha_envio.append(uid)

            # ---------- remove (só no multidirecional) ----------
            removidos, falha_remocao = [], []
            if modo.value == "multidirecional":
                for uid in sem_cargo:
                    try:
                        for msg in existentes[uid]:
                            await msg.delete()
                        removidos.append(uid)
                    except (discord.Forbidden, discord.HTTPException):
                        falha_remocao.append(uid)

        # ---------- logs ----------
        embed = discord.Embed(
            title="📋 Salvar cargos na thread",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Usado por", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="Cargo", value=f"{cargo.name} (`{cargo.id}`)", inline=True)
        embed.add_field(
            name="Thread",
            value=f"[{canal_thread.name}]({canal_thread.jump_url}) (`{canal_thread.id}`)",
            inline=True,
        )
        embed.add_field(
            name="Servidor da thread",
            value=f"{canal_thread.guild.name} (`{canal_thread.guild.id}`)",
            inline=True,
        )
        embed.add_field(
            name="Servidor do cargo",
            value=f"{guild.name} (`{guild.id}`)",
            inline=True,
        )
        embed.add_field(
            name="Modo",
            value="Multidirecional" if modo.value == "multidirecional" else "Adicionar apenas",
            inline=True,
        )
        embed.add_field(name="Membros com o cargo", value=str(len(ids_com_cargo)), inline=True)
        embed.add_field(name="Já estavam na thread", value=str(len(ids_com_cargo) - len(faltando)), inline=True)
        embed.add_field(name="Adicionados", value=str(len(adicionados)), inline=True)

        if modo.value == "multidirecional":
            embed.add_field(name="Removidos (sem o cargo)", value=str(len(removidos)), inline=True)
        else:
            embed.add_field(
                name="Sem o cargo, mantidos na thread",
                value=str(len(sem_cargo)),
                inline=True,
            )
        if falha_envio or falha_remocao:
            embed.add_field(
                name="⚠️ Falhas",
                value=f"Envio: {len(falha_envio)} | Remoção: {len(falha_remocao)}",
                inline=False,
            )

        listas = [("IDs adicionados", adicionados)]
        if modo.value == "multidirecional":
            listas.append(("IDs removidos (não possuem mais o cargo)", removidos))
        else:
            listas.append(("IDs que continuam na thread, mas não possuem o cargo", sem_cargo))
        listas += [
            ("Falha ao enviar", falha_envio),
            ("Falha ao remover", falha_remocao),
        ]

        await _enviar_logs(bot, embed, listas)

        await interaction.followup.send(
            f"✅ Concluído! Adicionados: **{len(adicionados)}** | "
            + (
                f"Removidos: **{len(removidos)}**"
                if modo.value == "multidirecional"
                else f"Sem o cargo (mantidos): **{len(sem_cargo)}**"
            )
            + (f" | ⚠️ Falhas: **{len(falha_envio) + len(falha_remocao)}**" if (falha_envio or falha_remocao) else ""),
            ephemeral=True,
        )