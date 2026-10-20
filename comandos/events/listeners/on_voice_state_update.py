import discord

from config.IDs import (
    canticos,
    eden,
    getsemani,
    jaco,
    laai_roi,
    oliveiras,
    salmos,
    sinai,
)


# CALLS INDEPENDENTES -> CALLS DEPENDENTES
CALLS_DEPENDENTES = {
    eden: getsemani,
    sinai: oliveiras,
    jaco: laai_roi,
    salmos: canticos
}


async def atualizar_call_dependente(
    guild: discord.Guild,
    call_independente_id: int,
    call_dependente_id: int
):

    call_independente = guild.get_channel(call_independente_id)
    call_dependente = guild.get_channel(call_dependente_id)

    # Verifica se as duas calls existem
    if not isinstance(call_independente, discord.VoiceChannel):
        print(
            f"[CALLS] Call independente não encontrada: "
            f"{call_independente_id}"
        )
        return

    if not isinstance(call_dependente, discord.VoiceChannel):
        print(
            f"[CALLS] Call dependente não encontrada: "
            f"{call_dependente_id}"
        )
        return

    # VERIFICAR QUEM ESTÁ NAS CALLS

    pessoas_na_independente = [
        membro
        for membro in call_independente.members
        if not membro.bot
    ]

    pessoas_na_dependente = [
        membro
        for membro in call_dependente.members
        if not membro.bot
    ]

    # DECIDIR SE A CALL DEPENDENTE DEVE SER VISÍVEL

    # Se houver alguém na independente:
    #     libera a dependente.
    #
    # Se a independente estiver vazia, mas ainda houver
    # alguém na dependente:
    #     mantém a dependente visível.
    #
    # Somente quando AMBAS estiverem vazias:
    #     esconde a dependente.

    deve_ser_visivel = (
        len(pessoas_na_independente) > 0
        or len(pessoas_na_dependente) > 0
    )

    # @EVERYONE
    everyone = guild.default_role

    # Pega as permissões atuais do @everyone
    overwrite = call_dependente.overwrites_for(everyone)

    # ALTERA SOMENTE "VER CANAL"
    overwrite.view_channel = deve_ser_visivel
    try:
        await call_dependente.set_permissions(
            everyone,
            overwrite=overwrite,
            reason="Atualização de call dependente"
        )

        print(
            f"[CALLS] "
            f"{call_independente.name} -> "
            f"{call_dependente.name} | "
            f"View Channel: {deve_ser_visivel}"
        )

    except discord.Forbidden:
        print(
            f"[CALLS] O bot não tem permissão para "
            f"alterar {call_dependente.name}."
        )

    except discord.HTTPException as erro:

        print(
            f"[CALLS] Erro ao alterar "
            f"{call_dependente.name}: {erro}"
        )


def registrar_evento_on_voice_state_update(bot):
    @bot.event
    async def on_voice_state_update(
        membro: discord.Member,
        antes: discord.VoiceState,
        depois: discord.VoiceState
    ):

        # Ignora bots
        if membro.bot:
            return

        guild = membro.guild

        # DESCOBRIR QUAIS PARES FORAM AFETADOS

        pares_afetados = set()

        for independente_id, dependente_id in CALLS_DEPENDENTES.items():
            # Saiu de uma call independente

            if antes.channel is not None:

                if antes.channel.id == independente_id:
                    pares_afetados.add(
                        (independente_id, dependente_id)
                    )

            # Entrou em uma call independente
            if depois.channel is not None:

                if depois.channel.id == independente_id:
                    pares_afetados.add(
                        (independente_id, dependente_id)
                    )

            # Saiu de uma call dependente
            if antes.channel is not None:

                if antes.channel.id == dependente_id:
                    pares_afetados.add(
                        (independente_id, dependente_id)
                    )

            # Entrou em uma call dependente
            if depois.channel is not None:

                if depois.channel.id == dependente_id:
                    pares_afetados.add(
                        (independente_id, dependente_id)
                    )

        # ATUALIZAR OS PARES AFETADOS
        for independente_id, dependente_id in pares_afetados:

            await atualizar_call_dependente(
                guild,
                independente_id,
                dependente_id
            )
