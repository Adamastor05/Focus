import discord


async def verificar_destaque_do_dia(
    bot,
    antes: discord.Member,
    depois: discord.Member,
    cargo_destaque_do_dia_id: int,
    chat_thread_ddd_logs_id: int
):

    # ============================================================
    # VERIFICAR SE O CARGO FOI ADICIONADO
    # ============================================================

    tinha_cargo = any(
        cargo.id == cargo_destaque_do_dia_id
        for cargo in antes.roles
    )

    tem_cargo = any(
        cargo.id == cargo_destaque_do_dia_id
        for cargo in depois.roles
    )

    # Só continua se a pessoa acabou de ganhar o cargo
    if tinha_cargo or not tem_cargo:
        return

    # ============================================================
    # ENCONTRAR A THREAD DE LOGS
    # ============================================================

    thread_logs = depois.guild.get_thread(
        chat_thread_ddd_logs_id
    )

    if thread_logs is None:
        try:
            thread_logs = await bot.fetch_channel(
                chat_thread_ddd_logs_id
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):
            print(
                "[DESTAQUE DO DIA] "
                "Não foi possível encontrar a thread de logs."
            )
            return

    # ============================================================
    # ENVIAR LOG
    # ============================================================

    try:

        await thread_logs.send(
            f"⭐ **Destaque do Dia recebido**\n\n"
            f"**Nome:** {depois.name}\n"
            f"**Apelido:** {depois.display_name}\n"
            f"**ID:** `{depois.id}`"
        )

    except discord.Forbidden:

        print(
            "[DESTAQUE DO DIA] "
            "Não tenho permissão para enviar mensagens "
            "na thread de logs."
        )

    except discord.HTTPException as e:

        print(
            f"[DESTAQUE DO DIA] "
            f"Erro ao enviar log: {e}"
        )