import asyncio
import re
import discord

from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURAÇÕES
# ============================================================

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")

INTERVALO_VERIFICACAO = 10  # segundos


# ============================================================
# INTERPRETAR UMA MENSAGEM AGENDADA
# ============================================================

def interpretar_agendamento(conteudo: str):

    dados = {
        "motivo": None,
        "pessoa_tem": None,
        "cargo": None,
        "onde": None,
        "quando": None,
        "mensagem": None
    }

    linhas = conteudo.splitlines()

    mensagem_index = None

    for i, linha in enumerate(linhas):

        linha_limpa = linha.strip()

        # ========================================================
        # MOTIVO
        # ========================================================

        if linha_limpa.lower().startswith("motivo:"):
            dados["motivo"] = linha_limpa[
                len("motivo:"):
            ].strip()

        # ========================================================
        # PESSOA_TEM
        # ========================================================

        elif linha_limpa.lower().startswith("pessoa_tem("):

            match = re.match(
                r"(?i)^pessoa_tem\((\d+)\)\s*:?\s*$",
                linha_limpa
            )

            if match:
                dados["pessoa_tem"] = int(
                    match.group(1)
                )

        # ========================================================
        # CARGO
        # ========================================================

        elif linha_limpa.lower().startswith("cargo("):

            match = re.match(
                r"(?i)^cargo\((\d+)\)\s*:?\s*$",
                linha_limpa
            )

            if match:
                dados["cargo"] = int(
                    match.group(1)
                )

        # ========================================================
        # ONDE
        # ========================================================

        elif linha_limpa.lower().startswith("onde:"):

            valor = linha_limpa[
                len("onde:"):
            ].strip()

            if valor:
                dados["onde"] = valor

        # ========================================================
        # QUANDO
        # ========================================================

        elif linha_limpa.lower().startswith("quando:"):

            valor = linha_limpa[
                len("quando:"):
            ].strip()

            try:

                dados["quando"] = datetime.strptime(
                    valor,
                    "%H:%M %d/%m/%Y"
                ).replace(
                    tzinfo=FUSO_BRASILIA
                )

            except ValueError:

                return None

        # ========================================================
        # MENSAGEM
        # ========================================================

        elif linha_limpa.lower().startswith("mensagem:"):

            mensagem_index = i

            # Pegamos TUDO depois de "Mensagem:"
            primeira_parte = linha[
                linha.lower().find("mensagem:") + len("mensagem:"):
            ].strip()

            partes = []

            if primeira_parte:
                partes.append(primeira_parte)

            # Caso a mensagem tenha várias linhas,
            # todas elas pertencem à mensagem.
            for restante in linhas[i + 1:]:
                partes.append(restante)

            dados["mensagem"] = "\n".join(
                partes
            ).strip()

            break

    # ============================================================
    # CAMPOS OBRIGATÓRIOS
    # ============================================================

    if dados["onde"] is None:
        return None

    if dados["quando"] is None:
        return None

    if dados["mensagem"] is None:
        return None

    if not dados["mensagem"]:
        return None

    return dados


# ============================================================
# LOCALIZAR THREAD PELO ID
# ============================================================

async def procurar_thread_por_id(
    bot,
    guild: discord.Guild,
    thread_id: int
):

    # --------------------------------------------------------
    # Tentar pelo cache
    # --------------------------------------------------------

    thread = guild.get_thread(thread_id)

    if thread is not None:
        return thread

    # --------------------------------------------------------
    # Tentar buscar diretamente
    # --------------------------------------------------------

    try:

        canal = await bot.fetch_channel(thread_id)

        if isinstance(canal, discord.Thread):
            return canal

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        pass

    return None


# ============================================================
# PROCURAR CHAT PELO ID DO USUÁRIO
# ============================================================

async def procurar_chat_por_id(
    bot,
    guild: discord.Guild,
    usuario_id: int,
    chat_conversas_id: int
):

    forum = guild.get_channel(chat_conversas_id)

    if forum is None:

        try:
            forum = await bot.fetch_channel(
                chat_conversas_id
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):
            return None

    # --------------------------------------------------------
    # Threads ativas
    # --------------------------------------------------------

    for thread in forum.threads:

        if str(usuario_id) in thread.name:
            return thread

    # --------------------------------------------------------
    # Threads arquivadas
    # --------------------------------------------------------

    try:

        async for thread in forum.archived_threads(
            limit=None
        ):

            if str(usuario_id) in thread.name:

                # Se estiver arquivada, desarquivar
                if thread.archived:

                    try:
                        await thread.edit(
                            archived=False
                        )
                    except (
                        discord.Forbidden,
                        discord.HTTPException
                    ):
                        return None

                return thread

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        return None

    return None


# ============================================================
# LOCALIZAR DESTINO
# ============================================================

async def localizar_destino(
    bot,
    guild: discord.Guild,
    onde: str,
    chat_conversas_id: int
):

    # ========================================================
    # PV_ID
    # ========================================================

    match = re.fullmatch(
        r"pv_(\d+)",
        onde,
        re.IGNORECASE
    )

    if match:

        usuario_id = int(match.group(1))

        try:

            usuario = await bot.fetch_user(
                usuario_id
            )

            return {
                "tipo": "pv",
                "destino": usuario
            }

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):
            return None

    # ========================================================
    # ;chat_ID
    # ========================================================

    match = re.fullmatch(
        r";chat_(\d+)",
        onde,
        re.IGNORECASE
    )

    if match:

        usuario_id = int(match.group(1))

        thread = await procurar_chat_por_id(
            bot,
            guild,
            usuario_id,
            chat_conversas_id
        )

        if thread is None:
            return None

        return {
            "tipo": "thread",
            "destino": thread
        }

    # ========================================================
    # ID NORMAL
    # ========================================================

    if onde.isdigit():

        canal_id = int(onde)

        # Tentar como canal/thread pelo cache/API
        destino = guild.get_channel(canal_id)

        if destino is None:

            try:

                destino = await bot.fetch_channel(
                    canal_id
                )

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                destino = None

        if destino is None:
            return None

        if isinstance(
            destino,
            (
                discord.TextChannel,
                discord.Thread,
                discord.VoiceChannel,
                discord.StageChannel
            )
        ):
            return {
                "tipo": "canal",
                "destino": destino
            }

    return None


# ============================================================
# VERIFICAR PESSOA_TEM E CARGO
# ============================================================

async def verificar_requisitos(
    bot,
    guild: discord.Guild,
    pessoa_tem_id: int | None,
    cargo_id: int | None
):

    # Nenhuma condição
    if pessoa_tem_id is None:
        return True

    # --------------------------------------------------------
    # Buscar pessoa
    # --------------------------------------------------------

    membro = guild.get_member(
        pessoa_tem_id
    )

    if membro is None:

        try:

            membro = await guild.fetch_member(
                pessoa_tem_id
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):
            return False

    # --------------------------------------------------------
    # Se não especificou cargo, basta a pessoa existir
    # --------------------------------------------------------

    if cargo_id is None:
        return True

    # --------------------------------------------------------
    # Verificar cargo
    # --------------------------------------------------------

    return any(
        cargo.id == cargo_id
        for cargo in membro.roles
    )


# ============================================================
# ENVIAR MENSAGEM
# ============================================================

async def enviar_mensagem_agendada(
    bot,
    guild: discord.Guild,
    dados: dict,
    chat_conversas_id: int
):

    destino_info = await localizar_destino(
        bot,
        guild,
        dados["onde"],
        chat_conversas_id
    )

    if destino_info is None:
        return False, "Destino não encontrado."

    destino = destino_info["destino"]

    # --------------------------------------------------------
    # PV
    # --------------------------------------------------------

    if destino_info["tipo"] == "pv":

        try:

            await destino.send(
                dados["mensagem"]
            )

            return True, "Mensagem enviada por PV."

        except discord.Forbidden:

            return False, "Não foi possível enviar o PV."

        except discord.HTTPException as e:

            return False, f"Erro ao enviar PV: {e}"

    # --------------------------------------------------------
    # Canal / Thread
    # --------------------------------------------------------

    try:

        # Se for thread arquivada, tentar desarquivar
        if isinstance(destino, discord.Thread):

            if destino.archived:

                await destino.edit(
                    archived=False
                )

        await destino.send(
            dados["mensagem"]
        )

        return True, "Mensagem enviada."

    except discord.Forbidden:

        return False, "Sem permissão para enviar mensagem."

    except discord.HTTPException as e:

        return False, f"Erro do Discord: {e}"


# ============================================================
# PROCESSAR UMA MENSAGEM AGENDADA
# ============================================================

async def processar_agendamento(
    bot,
    mensagem: discord.Message,
    chat_conversas_id: int,
    chat_logs_id: int
):

    dados = interpretar_agendamento(
        mensagem.content
    )

    if dados is None:
        print(
            f"[AGENDADOR] Mensagem {mensagem.id} "
            f"não possui um formato válido."
        )
        print(
            f"[AGENDADOR] Conteúdo recebido:\n"
            f"{mensagem.content}"
        )
        return

    # ========================================================
    # VERIFICAR HORÁRIO
    # ========================================================

    agora = datetime.now(
        FUSO_BRASILIA
    )

    if agora < dados["quando"]:
        return

    # ========================================================
    # VERIFICAR REQUISITOS
    # ========================================================

    requisitos_ok = await verificar_requisitos(
        bot,
        mensagem.guild,
        dados["pessoa_tem"],
        dados["cargo"]
    )

    if not requisitos_ok:
        return

    # ========================================================
    # ENVIAR
    # ========================================================

    sucesso, resultado = await enviar_mensagem_agendada(
        bot,
        mensagem.guild,
        dados,
        chat_conversas_id
    )

    if not sucesso:
        print(
            f"[AGENDADOR] "
            f"Não foi possível executar a mensagem "
            f"{mensagem.id}: {resultado}"
        )
        return

    # ========================================================
    # APAGAR AGENDAMENTO
    # ========================================================

    try:

        await mensagem.delete()

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        pass

    # ========================================================
    # LOG
    # ========================================================

    canal_logs = mensagem.guild.get_channel(
        chat_logs_id
    )

    if canal_logs is None:

        try:

            canal_logs = await bot.fetch_channel(
                chat_logs_id
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):
            canal_logs = None

    if canal_logs is None:
        return

    embed = discord.Embed(
        title="📅 Mensagem agendada executada",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )

    # --------------------------------------------------------
    # Pessoa que programou
    # --------------------------------------------------------

    if mensagem.author.id != bot.user.id:

        pessoa = (
            f"{mensagem.author.mention}\n"
            f"`{mensagem.author.id}`"
        )

    else:

        pessoa = "🤖 O próprio bot"

    embed.add_field(
        name="👤 Pessoa",
        value=pessoa,
        inline=False
    )

    # --------------------------------------------------------
    # Motivo
    # --------------------------------------------------------

    embed.add_field(
        name="📋 Motivo",
        value=(
            dados["motivo"]
            if dados["motivo"]
            else "Não informado."
        ),
        inline=False
    )

    # --------------------------------------------------------
    # Pessoa_tem
    # --------------------------------------------------------

    embed.add_field(
        name="👤 Pessoa_tem",
        value=(
            f"`{dados['pessoa_tem']}`"
            if dados["pessoa_tem"] is not None
            else "Não definido."
        ),
        inline=True
    )

    # --------------------------------------------------------
    # Cargo
    # --------------------------------------------------------

    embed.add_field(
        name="🎖️ Cargo",
        value=(
            f"<@&{dados['cargo']}>"
            if dados["cargo"] is not None
            else "Não definido."
        ),
        inline=True
    )

    # --------------------------------------------------------
    # Onde
    # --------------------------------------------------------

    embed.add_field(
        name="📍 Onde",
        value=f"`{dados['onde']}`",
        inline=False
    )

    # --------------------------------------------------------
    # Quando
    # --------------------------------------------------------

    embed.add_field(
        name="⏰ Quando",
        value=dados["quando"].strftime(
            "%H:%M %d/%m/%Y"
        ),
        inline=False
    )

    # --------------------------------------------------------
    # Mensagem
    # --------------------------------------------------------

    embed.add_field(
        name="💬 Mensagem",
        value=dados["mensagem"][:1024],
        inline=False
    )

    embed.add_field(
        name="📊 Resultado",
        value=resultado,
        inline=False
    )

    # --------------------------------------------------------
    # ID da mensagem que programou
    # --------------------------------------------------------

    embed.add_field(
        name="🆔 ID do agendamento",
        value=f"`{mensagem.id}`",
        inline=False
    )

    await canal_logs.send(
        embed=embed
    )


# ============================================================
# VERIFICAR TODAS AS MENSAGENS
# ============================================================
async def verificar_agendamentos(
    bot,
    chat_thread_agendar_msgs_id: int,
    chat_conversas_id: int,
    chat_logs_id: int
):

    # --------------------------------------------------------
    # Encontrar a thread
    # --------------------------------------------------------

    thread = bot.get_channel(
        chat_thread_agendar_msgs_id
    )

    if thread is None:

        try:

            thread = await bot.fetch_channel(
                chat_thread_agendar_msgs_id
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):
            return

    if not isinstance(
        thread,
        discord.Thread
    ):
        return

    # --------------------------------------------------------
    # Ler mensagens da thread
    # --------------------------------------------------------

    try:

        async for mensagem in thread.history(
            limit=None
        ):

            # Nunca processar mensagens de bots
            if mensagem.author.bot:
                continue

            # ------------------------------------------------
            # Verificar se é um agendamento válido
            # ------------------------------------------------

            dados = interpretar_agendamento(
                mensagem.content
            )

            # ------------------------------------------------
            # Se não for válido, apagar
            # ------------------------------------------------

            if dados is None:

                try:

                    await mensagem.delete()

                    print(
                        f"[AGENDADOR] "
                        f"Mensagem inválida apagada: "
                        f"{mensagem.id}"
                    )

                except (
                    discord.NotFound,
                    discord.Forbidden,
                    discord.HTTPException
                ) as e:

                    print(
                        f"[AGENDADOR] "
                        f"Não foi possível apagar "
                        f"a mensagem {mensagem.id}: {e}"
                    )

                continue

            # ------------------------------------------------
            # Se for válido, processar agendamento
            # ------------------------------------------------

            await processar_agendamento(
                bot,
                mensagem,
                chat_conversas_id,
                chat_logs_id
            )

    except (
        discord.Forbidden,
        discord.HTTPException
    ) as e:

        print(
            f"[AGENDADOR] Erro ao ler thread: {e}"
        )


# ============================================================
# LOOP DO AGENDADOR
# ============================================================

async def iniciar_agendador(
    bot,
    chat_thread_agendar_msgs_id: int,
    chat_conversas_id: int,
    chat_logs_id: int
):

    await bot.wait_until_ready()

    print(
        "[AGENDADOR] Sistema de mensagens agendadas iniciado."
    )

    while not bot.is_closed():

        try:

            await verificar_agendamentos(
                bot,
                chat_thread_agendar_msgs_id,
                chat_conversas_id,
                chat_logs_id
            )

        except Exception as e:

            print(
                f"[AGENDADOR] Erro no loop: {e}"
            )

        await asyncio.sleep(
            INTERVALO_VERIFICACAO
        )