"""Botão "Denunciar imagem" nos logs de análise de perfil.

Ao clicar, a imagem do log é tratada como imprópria: abre o tópico em
CHAT_PERFIS_SUSPEITOS (mesmo fluxo do que passou de 60), mas SEM marcar os moderadores.
O botão é persistente (continua funcionando depois de reiniciar o bot): a pessoa é
lida do "ID" da embed do log e a imagem, do anexo do próprio log.
"""
import re

import aiohttp
import discord

from comandos.slash.analisar_foto_perfil import baixar_avatar, log, tem_permissao
from sistemas.analise_pfp.perfil_suspeito import abrir_caso, buscar_caso_aberto

CUSTOM_ID = "denunciar_perfil"
PADRAO_ID = re.compile(r"ID:\*\*\s*`(\d{15,20})`")


async def _obter_imagem(msg: discord.Message, membro: discord.Member) -> tuple[bytes, bool]:
    """
    Retorna (imagem, exata). Tenta, em ordem:
    1) anexo da mensagem do clique; 2) anexo da mensagem recarregada;
    3) URL da imagem da embed; 4) foto atual da pessoa (exata=False).
    Cada falha é impressa no console para facilitar achar o motivo.
    """
    try:
        return await msg.attachments[0].read(), True
    except Exception as e:
        print(f"[PERFIL] Denúncia: anexo da mensagem do clique falhou: {e!r}")

    try:
        fresca = await msg.channel.fetch_message(msg.id)
        return await fresca.attachments[0].read(), True
    except Exception as e:
        print(f"[PERFIL] Denúncia: anexo da mensagem recarregada falhou: {e!r}")

    try:
        url = msg.embeds[0].image.url
        async with aiohttp.ClientSession() as sessao, sessao.get(url) as resp:
            resp.raise_for_status()
            return await resp.read(), True
    except Exception as e:
        print(f"[PERFIL] Denúncia: imagem da embed falhou: {e!r}")

    return await baixar_avatar(membro), False


class DenunciarView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    # secondary = botão cinza "transparente" (link não consegue chamar o bot)
    @discord.ui.button(
        label="Denunciar imagem",
        style=discord.ButtonStyle.secondary,
        custom_id=CUSTOM_ID,
    )
    async def denunciar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not tem_permissao(interaction.user):
            await interaction.response.send_message(
                "Você não tem permissão para usar esse botão.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        msg = interaction.message

        # pessoa: id na embed do log
        achado = PADRAO_ID.search(msg.embeds[0].description or "") if msg.embeds else None
        if not achado:
            await interaction.followup.send(
                "Não consegui ler o id da pessoa nesse log.", ephemeral=True
            )
            return
        uid = int(achado.group(1))

        # já existe tópico aberto?
        existente = buscar_caso_aberto(self.bot, uid)
        if existente:
            await interaction.followup.send(
                f"Já existe um tópico aberto para essa pessoa: {existente.mention}", ephemeral=True
            )
            return

        guild = interaction.guild
        membro = guild.get_member(uid)
        if membro is None:
            try:
                membro = await guild.fetch_member(uid)
            except discord.HTTPException:
                await interaction.followup.send(
                    "Essa pessoa não está mais no servidor.", ephemeral=True
                )
                return

        # imagem: a foto exata do log; se não der, a foto atual da pessoa
        try:
            imagem, exata = await _obter_imagem(msg, membro)
        except Exception as e:
            print(f"[PERFIL] Denúncia: não consegui obter nenhuma imagem: {e!r}")
            await interaction.followup.send(
                "Não consegui pegar a imagem desse log.", ephemeral=True
            )
            return

        try:
            thread = await abrir_caso(
                self.bot, membro, imagem, {}, denunciante=interaction.user
            )
        except Exception as e:
            print(f"[PERFIL] Erro ao abrir denúncia de {membro} ({membro.id}): {e}")
            await interaction.followup.send(
                "Deu erro ao abrir o tópico. Tente novamente.", ephemeral=True
            )
            return

        # desativa o botão (view nova, porque a registrada é compartilhada) e liga ao tópico
        try:
            nova = DenunciarView(self.bot)
            for item in nova.children:
                item.disabled = True
                item.label = "Imagem denunciada"
            embed = msg.embeds[0]
            embed.add_field(name="Tópico de revisão", value=thread.mention, inline=False)
            await msg.edit(embed=embed, view=nova)
        except discord.HTTPException:
            pass

        aviso = "" if exata else (
            "\n⚠️ Não consegui ler a imagem do log, então usei a foto atual da pessoa."
        )
        await interaction.followup.send(f"Tópico aberto: {thread.mention}{aviso}", ephemeral=True)
        await log(
            self.bot,
            "Perfil: imagem denunciada",
            f"Por: {interaction.user} ({interaction.user.id})\n"
            f"Pessoa: {membro} ({membro.id})\nTópico: {thread.mention}",
        )


def registrar_denuncia_perfil(bot):
    """Registra a view persistente quando o bot ficar pronto (precisa de loop rodando)."""
    registrado = False

    @bot.listen("on_ready")
    async def perfil_denuncia_on_ready():
        nonlocal registrado
        if not registrado:
            bot.add_view(DenunciarView(bot))
            registrado = True
