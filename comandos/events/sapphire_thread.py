import discord


chat_leitura_diaria = 1417906970706579599
sapphire_id = 678344927997853742
chat_logs = 1523110468124803204


async def registrar_log(bot, texto):
    canal = bot.get_channel(chat_logs)

    if canal is not None:
        await canal.send(texto)


async def verificar_thread_sapphire(bot):
    canal = bot.get_channel(chat_leitura_diaria)

    if canal is None:
        print("❌ Canal de leitura diária não encontrado.")
        return

    try:
        # Pega somente a mensagem mais recente
        mensagem = await canal.fetch_message(
            (await canal.history(limit=1).__anext__()).id
        )

        print(
            f"🔎 Mensagem mais recente: {mensagem.id} | "
            f"Autor: {mensagem.author} ({mensagem.author.id})"
        )

        # Se não for a Sapphire, não faz absolutamente nada
        if mensagem.author.id != sapphire_id:
            print("ℹ️ A mensagem mais recente não é da Sapphire.")
            return

        # Verifica se existe uma thread nessa mensagem
        thread = mensagem.thread

        if thread is None:
            print("ℹ️ A mensagem da Sapphire não possui thread.")
            return

        thread_id = thread.id
        thread_name = thread.name

        await thread.delete(
            reason="Thread criada em mensagem da Sapphire"
        )

        print(f"🗑️ Thread apagada: {thread_name} ({thread_id})")

        await registrar_log(
            bot,
            f"🗑️ **Thread apagada**\n"
            f"Mensagem da Sapphire em <#{chat_leitura_diaria}>\n"
            f"Thread: `{thread_name}` (`{thread_id}`)"
        )

    except discord.NotFound:
        print("❌ Mensagem, canal ou thread não encontrada.")

    except discord.Forbidden:
        print("❌ O bot não tem permissão para apagar a thread.")

        await registrar_log(
            bot,
            f"❌ Não consegui apagar uma thread da Sapphire em "
            f"<#{chat_leitura_diaria}>: sem permissão."
        )

    except discord.HTTPException as e:
        print(f"❌ Erro do Discord: {e}")


async def on_thread_create(thread: discord.Thread):
    # Só interessa ao canal de leitura diária
    if thread.parent_id != chat_leitura_diaria:
        return

    try:
        # A mensagem que originou a thread possui o mesmo ID da thread
        mensagem = await thread.parent.fetch_message(thread.id)

        print(
            f"🧵 Nova thread detectada: {thread.name} | "
            f"Autor da mensagem: {mensagem.author} ({mensagem.author.id})"
        )

        # Se não foi a Sapphire, não faz nada
        if mensagem.author.id != sapphire_id:
            return

        bot = thread.guild._state._get_client()

        await thread.delete(
            reason="Thread criada em mensagem da Sapphire"
        )

        print(f"🗑️ Thread da Sapphire apagada: {thread.name}")

        await registrar_log(
            bot,
            f"🗑️ **Thread apagada automaticamente**\n"
            f"Thread: `{thread.name}` (`{thread.id}`)\n"
            f"Motivo: criada na mensagem da Sapphire."
        )

    except discord.NotFound:
        print("❌ Não foi possível encontrar a mensagem inicial da thread.")

    except discord.Forbidden:
        print(
            f"❌ Sem permissão para apagar a thread "
            f"`{thread.name}`."
        )

    except discord.HTTPException as e:
        print(f"❌ Erro ao processar thread: {e}")