import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import discord
from discord import app_commands


# ============================================================
# CONFIGURAÇÃO
# ============================================================

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


CATEGORIAS_ANALISADAS = {
    1347727626910826549,  # comunidade
    1466983138633842851,  # caminhada cristã
    1353528134846386197,  # estudo da bíblia
    1451631718791381043,  # bots
}


# Chats fora das categorias.
CHATS_EXTRAS = {
    1363009444111188129,  # apresentações
}


# Chat que contém IDs de usuários.
CHAT_IDS_APARICOES = 1470584162225492008


# Chats completamente ignorados.
# O próprio chat e todas as suas threads serão ignorados.
CHATS_IGNORADOS = {
    1347727626910826554,  # chat_divulgacoes
}


# Categoria onde ficam as calls.
CATEGORIA_CALL = 1366380263302758450


# Thread onde o resultado será enviado.
THREAD_ULTIMAS_APARICOES = 1549993152021135542


# ============================================================
# CONTROLE DA TAREFA
# ============================================================

_tarefa_aparicoes = None
_ultima_data_automatica = None


# ============================================================
# DATA / HORA
# ============================================================

def agora_brasilia():
    return datetime.now(FUSO_BRASILIA)


def intervalo_do_dia(data):
    inicio = datetime(
        data.year,
        data.month,
        data.day,
        0,
        0,
        0,
        0,
        tzinfo=FUSO_BRASILIA,
    )

    fim = inicio + timedelta(days=1)

    return inicio, fim


def converter_para_utc(data_hora):
    return data_hora.astimezone(timezone.utc)


# ============================================================
# VERIFICAR IGNORADOS
# ============================================================

def canal_ignorado(canal):

    if canal.id in CHATS_IGNORADOS:
        return True

    if isinstance(canal, discord.Thread):

        if canal.parent_id in CHATS_IGNORADOS:
            return True

        if canal.parent is not None:

            if canal.parent.id in CHATS_IGNORADOS:
                return True

    return False


# ============================================================
# VERIFICAR SE UMA THREAD PODE TER ATIVIDADE ONTEM
# ============================================================

def thread_pode_ter_atividade_ontem(
    thread,
    inicio_utc,
    fim_utc,
):
    """
    Decide se vale a pena abrir o histórico da thread.

    A ideia é evitar analisar threads antigas que já estavam
    encerradas/arquivadas antes do início do dia analisado.

    Se não conseguirmos determinar com segurança a data da
    atividade, retornamos True para não perder uma aparição.
    """

    if thread is None:
        return False

    if canal_ignorado(thread):
        return False

    # --------------------------------------------------------
    # ÚLTIMA MENSAGEM CONHECIDA
    # --------------------------------------------------------

    ultima_mensagem = getattr(
        thread,
        "last_message_id",
        None,
    )

    # Não conseguimos determinar a última mensagem.
    # Nesse caso, é mais seguro analisar.
    if ultima_mensagem is None:
        return True

    try:

        mensagem_id = discord.Object(
            id=ultima_mensagem
        )

        # Discord snowflake contém timestamp.
        timestamp = discord.utils.snowflake_time(
            mensagem_id.id
        )

        # Se a última mensagem foi antes de ontem,
        # não há necessidade de procurar.
        if timestamp < inicio_utc:
            return False

        # Se a última mensagem foi ontem ou depois,
        # a thread pode conter mensagens de ontem.
        return True

    except Exception:

        return True


# ============================================================
# LER MENSAGENS DE UM CANAL
# ============================================================

async def coletar_autores_do_canal(
    canal,
    inicio_utc,
    fim_utc,
    ids,
):

    if canal is None:
        return

    if canal_ignorado(canal):
        return

    if isinstance(
        canal,
        discord.ForumChannel
    ):
        return

    try:

        async for mensagem in canal.history(
            limit=None,
            after=inicio_utc,
            before=fim_utc,
            oldest_first=True,
        ):

            # Segurança adicional.
            #
            # Se por qualquer motivo o Discord devolver uma
            # mensagem fora do intervalo, não contamos.
            if mensagem.created_at < inicio_utc:
                continue

            if mensagem.created_at >= fim_utc:
                break

            if mensagem.author.bot:
                continue

            ids.add(
                mensagem.author.id
            )

    except discord.Forbidden:

        print(
            f"[APARIÇÕES] Sem permissão para ler "
            f"{canal} ({canal.id})."
        )

    except discord.HTTPException as e:

        print(
            f"[APARIÇÕES] Erro HTTP ao ler "
            f"{canal} ({canal.id}): {e}"
        )

    except Exception as e:

        print(
            f"[APARIÇÕES] Erro ao ler "
            f"{canal} ({canal.id}): {e}"
        )


# ============================================================
# ANALISAR THREADS DE UM FÓRUM
# ============================================================

async def coletar_threads_do_forum(
    forum,
    inicio_utc,
    fim_utc,
    ids,
):

    if forum is None:
        return

    if canal_ignorado(forum):
        return

    threads_analisadas = set()

    print(
        f"[APARIÇÕES] Analisando fórum: "
        f"{forum.name} ({forum.id})"
    )

    # ========================================================
    # THREADS ATIVAS
    # ========================================================

    try:

        for thread in forum.threads:

            if thread.id in threads_analisadas:
                continue

            threads_analisadas.add(
                thread.id
            )

            if not thread_pode_ter_atividade_ontem(
                thread,
                inicio_utc,
                fim_utc,
            ):
                continue

            await coletar_autores_do_canal(
                thread,
                inicio_utc,
                fim_utc,
                ids,
            )

    except Exception as e:

        print(
            f"[APARIÇÕES] Erro nas threads ativas "
            f"do fórum {forum.id}: {e}"
        )

    # ========================================================
    # THREADS ARQUIVADAS
    # ========================================================

    try:

        async for thread in forum.archived_threads(
            limit=None
        ):

            if thread.id in threads_analisadas:
                continue

            threads_analisadas.add(
                thread.id
            )

            if not thread_pode_ter_atividade_ontem(
                thread,
                inicio_utc,
                fim_utc,
            ):
                continue

            await coletar_autores_do_canal(
                thread,
                inicio_utc,
                fim_utc,
                ids,
            )

    except discord.Forbidden:

        print(
            f"[APARIÇÕES] Sem permissão para acessar "
            f"threads arquivadas do fórum {forum.id}."
        )

    except discord.HTTPException as e:

        print(
            f"[APARIÇÕES] Erro HTTP nas threads arquivadas "
            f"do fórum {forum.id}: {e}"
        )

    except Exception as e:

        print(
            f"[APARIÇÕES] Erro nas threads arquivadas "
            f"do fórum {forum.id}: {e}"
        )


# ============================================================
# ANALISAR UMA CATEGORIA
# ============================================================

async def coletar_canais_da_categoria(
    categoria,
    inicio_utc,
    fim_utc,
    ids,
):

    if categoria is None:
        return

    if canal_ignorado(categoria):
        return

    print(
        f"[APARIÇÕES] Analisando categoria: "
        f"{categoria.name} ({categoria.id})"
    )

    # ========================================================
    # CANAIS DENTRO DA CATEGORIA
    # ========================================================

    for canal in categoria.channels:

        if canal_ignorado(canal):
            continue

        # ====================================================
        # FÓRUM
        # ====================================================

        if isinstance(
            canal,
            discord.ForumChannel
        ):

            await coletar_threads_do_forum(
                canal,
                inicio_utc,
                fim_utc,
                ids,
            )

            continue

        # ====================================================
        # CANAL DE TEXTO
        # ====================================================

        if isinstance(
            canal,
            discord.TextChannel
        ):

            print(
                f"[APARIÇÕES] Lendo canal: "
                f"{canal.name} ({canal.id})"
            )

            await coletar_autores_do_canal(
                canal,
                inicio_utc,
                fim_utc,
                ids,
            )

            continue

        # ====================================================
        # OUTROS
        # ====================================================

        print(
            f"[APARIÇÕES] Ignorando canal "
            f"{canal.name} ({canal.id}) "
            f"({type(canal).__name__})."
        )


# ============================================================
# CHATS EXTRAS
# ============================================================

async def coletar_chat_extra(
    chat,
    inicio_utc,
    fim_utc,
    ids,
):

    if chat is None:
        return

    if canal_ignorado(chat):
        return

    # Fórum.
    if isinstance(
        chat,
        discord.ForumChannel
    ):

        await coletar_threads_do_forum(
            chat,
            inicio_utc,
            fim_utc,
            ids,
        )

        return

    # Canal de texto.
    if isinstance(
        chat,
        discord.TextChannel
    ):

        await coletar_autores_do_canal(
            chat,
            inicio_utc,
            fim_utc,
            ids,
        )

        return

    # Thread.
    if isinstance(
        chat,
        discord.Thread
    ):

        await coletar_autores_do_canal(
            chat,
            inicio_utc,
            fim_utc,
            ids,
        )


# ============================================================
# CHAT DE IDS
# ============================================================

async def coletar_ids_do_chat(
    guild,
    inicio_utc,
    fim_utc,
    ids,
):

    chat = guild.get_channel(
        CHAT_IDS_APARICOES
    )

    if chat is None:

        print(
            f"[APARIÇÕES] Chat de IDs não encontrado: "
            f"{CHAT_IDS_APARICOES}"
        )

        return

    if canal_ignorado(chat):
        return

    print(
        f"[APARIÇÕES] Analisando chat de IDs: "
        f"{CHAT_IDS_APARICOES}"
    )

    try:

        async for mensagem in chat.history(
            limit=None,
            after=inicio_utc,
            before=fim_utc,
            oldest_first=True,
        ):

            if mensagem.created_at < inicio_utc:
                continue

            if mensagem.created_at >= fim_utc:
                break

            if mensagem.author.bot:
                continue

            conteudo = mensagem.content.strip()

            # A mensagem inteira precisa ser somente números.
            if not conteudo.isdigit():
                continue

            try:

                usuario_id = int(
                    conteudo
                )

            except ValueError:

                continue

            membro = guild.get_member(
                usuario_id
            )

            if membro is None:
                continue

            if membro.bot:
                continue

            ids.add(
                usuario_id
            )

            try:

                await mensagem.add_reaction(
                    "✅"
                )

            except discord.Forbidden:

                print(
                    f"[APARIÇÕES] Sem permissão para reagir "
                    f"à mensagem {mensagem.id}."
                )

            except discord.HTTPException as e:

                print(
                    f"[APARIÇÕES] Erro ao reagir à mensagem "
                    f"{mensagem.id}: {e}"
                )

    except discord.Forbidden:

        print(
            "[APARIÇÕES] Sem permissão para ler "
            "o chat de IDs."
        )

    except discord.HTTPException as e:

        print(
            f"[APARIÇÕES] Erro HTTP ao ler "
            f"o chat de IDs: {e}"
        )

    except Exception as e:

        print(
            f"[APARIÇÕES] Erro ao analisar "
            f"o chat de IDs: {e}"
        )


# ============================================================
# CALLS
# ============================================================

def coletar_pessoas_em_call(
    guild,
    ids,
):

    print(
        "[APARIÇÕES] Verificando pessoas em call..."
    )

    for canal in guild.voice_channels:

        if canal.category_id != CATEGORIA_CALL:
            continue

        for membro in canal.members:

            if membro.bot:
                continue

            ids.add(
                membro.id
            )


# ============================================================
# COLETA PRINCIPAL
# ============================================================

async def coletar_aparicoes_do_dia_anterior(
    guild,
):

    agora = agora_brasilia()

    data_analisada = (
        agora.date()
        - timedelta(days=1)
    )

    inicio_brasilia, fim_brasilia = (
        intervalo_do_dia(
            data_analisada
        )
    )

    inicio_utc = converter_para_utc(
        inicio_brasilia
    )

    fim_utc = converter_para_utc(
        fim_brasilia
    )

    ids = set()

    print(
        "============================================================"
    )

    print(
        f"[APARIÇÕES] Analisando "
        f"{data_analisada.strftime('%Y-%m-%d')}"
    )

    print(
        f"[APARIÇÕES] Início UTC: {inicio_utc}"
    )

    print(
        f"[APARIÇÕES] Fim UTC: {fim_utc}"
    )

    print(
        "============================================================"
    )

    # ========================================================
    # CATEGORIAS
    # ========================================================

    for categoria_id in CATEGORIAS_ANALISADAS:

        if categoria_id in CHATS_IGNORADOS:
            continue

        categoria = guild.get_channel(
            categoria_id
        )

        if categoria is None:

            print(
                f"[APARIÇÕES] Categoria não encontrada: "
                f"{categoria_id}"
            )

            continue

        await coletar_canais_da_categoria(
            categoria,
            inicio_utc,
            fim_utc,
            ids,
        )

    # ========================================================
    # CHATS EXTRAS
    # ========================================================

    for chat_id in CHATS_EXTRAS:

        if chat_id in CHATS_IGNORADOS:
            continue

        chat = guild.get_channel(
            chat_id
        )

        if chat is None:

            print(
                f"[APARIÇÕES] Chat extra não encontrado: "
                f"{chat_id}"
            )

            continue

        await coletar_chat_extra(
            chat,
            inicio_utc,
            fim_utc,
            ids,
        )

    # ========================================================
    # CHAT DE IDS
    # ========================================================

    await coletar_ids_do_chat(
        guild,
        inicio_utc,
        fim_utc,
        ids,
    )

    # ========================================================
    # CALLS
    # ========================================================

    coletar_pessoas_em_call(
        guild,
        ids,
    )

    print(
        f"[APARIÇÕES] Total de pessoas encontradas: "
        f"{len(ids)}"
    )

    return data_analisada, ids


# ============================================================
# ENVIAR RESULTADO
# ============================================================

async def registrar_aparicoes(
    bot,
    guild,
):

    data_analisada, ids = (
        await coletar_aparicoes_do_dia_anterior(
            guild
        )
    )

    thread = bot.get_channel(
        THREAD_ULTIMAS_APARICOES
    )

    if thread is None:

        try:

            thread = await bot.fetch_channel(
                THREAD_ULTIMAS_APARICOES
            )

        except Exception as e:

            print(
                f"[APARIÇÕES] Não foi possível encontrar "
                f"a thread {THREAD_ULTIMAS_APARICOES}: {e}"
            )

            return False

    ids_ordenados = sorted(
        ids
    )

    ids_texto = ",".join(
        str(usuario_id)
        for usuario_id in ids_ordenados
    )

    mensagem = (
        f"APARICOES|"
        f"{data_analisada.strftime('%Y-%m-%d')}|"
        f"{ids_texto}"
    )

    if len(mensagem) > 2000:

        print(
            "[APARIÇÕES] ERRO: a mensagem ultrapassou "
            "2000 caracteres."
        )

        print(
            f"[APARIÇÕES] Quantidade de IDs: "
            f"{len(ids_ordenados)}"
        )

        return False

    try:

        await thread.send(
            mensagem
        )

    except discord.Forbidden:

        print(
            "[APARIÇÕES] Sem permissão para enviar "
            "mensagem na thread."
        )

        return False

    except discord.HTTPException as e:

        print(
            f"[APARIÇÕES] Erro ao enviar mensagem: {e}"
        )

        return False

    print(
        f"[APARIÇÕES] Registradas "
        f"{len(ids_ordenados)} pessoas em "
        f"{data_analisada.strftime('%Y-%m-%d')}."
    )

    return True


# ============================================================
# SLASH COMMAND
# ============================================================

def registrar_aparicoes_diarias(
    bot,
    cargo_administrador,
    cargo_focus_adm,
):

    grupo = app_commands.Group(
        name="aparicoes",
        description="Comandos de aparições."
    )

    @grupo.command(
        name="diarias",
        description="Registra as aparições do dia anterior."
    )
    async def aparicoes_diarias(
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado no servidor.",
                ephemeral=True,
            )

            return

        membro = interaction.user

        if not isinstance(
            membro,
            discord.Member
        ):

            await interaction.response.send_message(
                "❌ Não foi possível verificar seus cargos.",
                ephemeral=True,
            )

            return

        cargos = {
            cargo.id
            for cargo in membro.roles
        }

        if (
            cargo_administrador not in cargos
            and cargo_focus_adm not in cargos
        ):

            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.",
                ephemeral=True,
            )

            return

        await interaction.response.send_message(
            "⏳ Iniciando a análise das aparições de ontem...",
            ephemeral=True,
        )

        sucesso = await registrar_aparicoes(
            bot,
            interaction.guild,
        )

        if sucesso:

            data_analisada = (
                agora_brasilia().date()
                - timedelta(days=1)
            )

            await interaction.edit_original_response(
                content=(
                    "✅ Aparições registradas.\n"
                    f"-# Data analisada: "
                    f"`{data_analisada.strftime('%Y-%m-%d')}`"
                )
            )

        else:

            await interaction.edit_original_response(
                content=(
                    "❌ Não foi possível registrar "
                    "as aparições."
                )
            )

    bot.tree.add_command(
        grupo
    )


# ============================================================
# TAREFA AUTOMÁTICA
# ============================================================

async def tarefa_aparicoes_diarias(
    bot,
):

    global _ultima_data_automatica

    await bot.wait_until_ready()

    while not bot.is_closed():

        try:

            agora = agora_brasilia()

            proxima_meia_noite = datetime(
                agora.year,
                agora.month,
                agora.day,
                0,
                0,
                0,
                0,
                tzinfo=FUSO_BRASILIA,
            ) + timedelta(days=1)

            segundos = (
                proxima_meia_noite - agora
            ).total_seconds()

            print(
                f"[APARIÇÕES] Próxima execução automática "
                f"em aproximadamente {segundos:.0f} segundos."
            )

            await asyncio.sleep(
                max(
                    segundos,
                    1
                )
            )

            agora = agora_brasilia()

            data_execucao = agora.date()

            if (
                _ultima_data_automatica
                == data_execucao
            ):
                continue

            _ultima_data_automatica = data_execucao

            print(
                "[APARIÇÕES] Meia-noite atingida. "
                "Iniciando registro automático."
            )

            for guild in bot.guilds:

                try:

                    await registrar_aparicoes(
                        bot,
                        guild,
                    )

                except Exception as e:

                    print(
                        f"[APARIÇÕES] Erro ao processar "
                        f"servidor {guild.id}: {e}"
                    )

        except asyncio.CancelledError:

            print(
                "[APARIÇÕES] Tarefa automática cancelada."
            )

            raise

        except Exception as e:

            print(
                f"[APARIÇÕES] Erro na tarefa automática: {e}"
            )

            await asyncio.sleep(10)


# ============================================================
# INICIAR TAREFA
# ============================================================

def iniciar_tarefa_aparicoes_diarias(
    bot,
):

    global _tarefa_aparicoes

    if (
        _tarefa_aparicoes is None
        or _tarefa_aparicoes.done()
    ):

        _tarefa_aparicoes = asyncio.create_task(
            tarefa_aparicoes_diarias(
                bot
            )
        )

    return _tarefa_aparicoes