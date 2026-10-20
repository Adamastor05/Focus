from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands


def formatar_tempo(td: timedelta) -> str:
    dias = td.days
    horas = td.seconds // 3600
    minutos = (td.seconds % 3600) // 60

    partes = []

    if dias:
        partes.append(f"{dias}d")
    if horas:
        partes.append(f"{horas}h")
    if minutos:
        partes.append(f"{minutos}min")

    return " ".join(partes) if partes else "<1min"


def deve_ser_verificado(
    membro: discord.Member,
    a_verificar_id: int,
    cargo_conta_suspeita_id: int,
    cargo_pedir_acesso_id: int,
) -> bool:
    cargos = {cargo.id for cargo in membro.roles}
    return (
        a_verificar_id in cargos
        or (
            cargo_conta_suspeita_id in cargos
            and cargo_pedir_acesso_id in cargos
        )
    )


class ViewExpulsar(discord.ui.View):
    def __init__(
        self,
        autor: discord.Member,
        a_verificar_id: int,
        cargo_conta_suspeita_id: int,
        cargo_pedir_acesso_id: int,
    ) -> None:
        super().__init__(timeout=10)
        self.autor = autor
        self.a_verificar_id = a_verificar_id
        self.cargo_conta_suspeita_id = cargo_conta_suspeita_id
        self.cargo_pedir_acesso_id = cargo_pedir_acesso_id
        self.msg: discord.Message | None = None

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

        if self.msg:
            await self.msg.edit(view=self)

    @discord.ui.button(
        label="Expulsar 3d+",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
    )
    async def expulsar(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button,
    ) -> None:
        if interaction.user != self.autor:
            await interaction.response.send_message(
                "Apenas quem executou o comando pode usar este botão.",
                ephemeral=True,
            )
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                "Este botão só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        limite = datetime.now(timezone.utc) - timedelta(days=3)
        expulsos = 0

        for membro in interaction.guild.members:
            if not deve_ser_verificado(
                membro,
                self.a_verificar_id,
                self.cargo_conta_suspeita_id,
                self.cargo_pedir_acesso_id,
            ):
                continue

            if membro.joined_at and membro.joined_at < limite:
                try:
                    await membro.kick(
                        reason=f"Limpeza automática por {interaction.user}"
                    )
                    expulsos += 1
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=f"✅ {expulsos} membro(s) foram expulsos.",
            view=self,
        )


def registrar_comando_verificar_a_verificar(
    bot: commands.Bot,
    cargo_moderador_id: int,
    a_verificar_id: int,
    cargo_conta_suspeita_id: int,
    cargo_pedir_acesso_id: int,
) -> None:
    @bot.tree.command(
        name="verificar_a_verificar",
        description=(
            "Verifica membros com cargo de análise ou conta suspeita "
            "aguardando acesso."
        ),
    )
    async def verificar_a_verificar(
        interaction: discord.Interaction,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        if not any(
            role.id == cargo_moderador_id
            for role in interaction.user.roles
        ):
            await interaction.response.send_message(
                "Você não possui permissão.",
                ephemeral=True,
            )
            return

        membros = [
            membro
            for membro in interaction.guild.members
            if deve_ser_verificado(
                membro,
                a_verificar_id,
                cargo_conta_suspeita_id,
                cargo_pedir_acesso_id,
            )
        ]

        if not membros:
            await interaction.response.send_message(
                "Nenhum membro encontrado.",
                ephemeral=True,
            )
            return

        agora = datetime.now(timezone.utc)
        linhas = []

        for membro in membros:
            if membro.joined_at is None:
                continue

            tempo_servidor = agora - membro.joined_at
            idade_conta_ao_entrar = membro.joined_at - membro.created_at
            info = []

            if any(role.id == a_verificar_id for role in membro.roles):
                info.append("A verificar")

            if (
                any(
                    role.id == cargo_conta_suspeita_id
                    for role in membro.roles
                )
                and any(
                    role.id == cargo_pedir_acesso_id
                    for role in membro.roles
                )
            ):
                info.append("Conta suspeita + Pedir acesso")

            linhas.append(
                f"**{membro}** ({' | '.join(info)})\n"
                f"• Conta ao entrar: "
                f"{formatar_tempo(idade_conta_ao_entrar)}\n"
                f"• No servidor: {formatar_tempo(tempo_servidor)}"
            )

        texto = "\n\n".join(linhas)
        if len(texto) > 1900:
            texto = texto[:1900] + "\n..."

        view = ViewExpulsar(
            interaction.user,
            a_verificar_id,
            cargo_conta_suspeita_id,
            cargo_pedir_acesso_id,
        )
        await interaction.response.send_message(
            texto,
            view=view,
            ephemeral=True,
        )
        view.msg = await interaction.original_response()
