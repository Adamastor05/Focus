import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands


# ============================================================
# CONFIGURAÇÃO
# ============================================================

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


# ============================================================
# IDS
# ============================================================

# Thread de Últimas Aparições
THREAD_ULTIMAS_APARICOES = 1549993152021135542

# Chat de logs
CHAT_LOGS = 1523110468124803204

# Cargo PRÓDIGOS
CARGO_PRODIGOS = 1549992943094468628

# Cargo DISCÍPULOS
CARGO_DISCIPULOS = 1425322037110374450


# ============================================================
# CONTROLE DA TAREFA AUTOMÁTICA
# ============================================================

_tarefa_prodigos = None

_ultima_execucao_automatica = None


# ============================================================
# HORÁRIO DE BRASÍLIA
# ============================================================

def agora_brasilia():
    return datetime.now(FUSO_BRASILIA)


# ============================================================
# LER UMA MENSAGEM DE APARIÇÕES
# ============================================================

def ler_aparicoes(mensagem):
    """
    Espera uma mensagem neste formato:

    APARICOES|2026-09-29|123,456,789
    """

    conteudo = mensagem.content.strip()

    partes = conteudo.split("|")

    if len(partes) != 3:
        return None

    if partes[0].strip().upper() != "APARICOES":
        return None

    data_texto = partes[1].strip()

    ids_texto = partes[2].strip()

    try:

        data = datetime.strptime(
            data_texto,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        return None

    ids = set()

    if ids_texto:

        for id_texto in ids_texto.split(","):

            id_texto = id_texto.strip()

            if not id_texto:
                continue

            if not id_texto.isdigit():
                continue

            ids.add(
                int(id_texto)
            )

    return data, ids


# ============================================================
# PEGAR AS ÚLTIMAS 32 MENSAGENS
# ============================================================

async def obter_32_aparicoes(thread):
    """
    A thread possui exatamente uma mensagem por dia.

    Portanto, basta pegar as últimas 32 mensagens válidas
    da thread.
    """

    mensagens = []

    print(
        "[PRÓDIGOS] Buscando as últimas 32 mensagens "
        "da thread de Últimas Aparições..."
    )

    try:

        async for mensagem in thread.history(
            limit=32,
            oldest_first=False,
        ):

            resultado = ler_aparicoes(
                mensagem
            )

            if resultado is None:
                continue

            data, ids = resultado

            mensagens.append(
                (
                    data,
                    ids,
                )
            )

            if len(mensagens) >= 32:
                break

    except discord.Forbidden:

        print(
            "[PRÓDIGOS] Sem permissão para ler "
            "a thread de Últimas Aparições."
        )

        return None

    except discord.HTTPException as e:

        print(
            f"[PRÓDIGOS] Erro HTTP ao ler a thread: {e}"
        )

        return None

    except Exception as e:

        print(
            f"[PRÓDIGOS] Erro ao ler a thread: {e}"
        )

        return None

    if len(mensagens) < 32:

        print(
            f"[PRÓDIGOS] Foram encontradas apenas "
            f"{len(mensagens)} mensagens de aparições. "
            f"São necessárias 32."
        )

        return None

    # history() veio do mais recente para o mais antigo.
    #
    # Inverter para ficar:
    #
    # [dia 1, dia 2, ..., dia 32]

    mensagens.reverse()

    return mensagens


# ============================================================
# ENCONTRAR PRÓDIGOS
# ============================================================

def encontrar_prodigos(
    aparicoes,
):
    """
    aparicoes contém:

        [dia 1, dia 2, ..., dia 32]

    Regra:

    - apareceu no dia 1 OU dia 2;
    - NÃO apareceu em nenhum dos outros 30 dias.
    """

    dia_1, ids_dia_1 = aparicoes[0]

    dia_2, ids_dia_2 = aparicoes[1]

    # Pessoas que apareceram no primeiro OU segundo dia.
    candidatos = (
        ids_dia_1
        | ids_dia_2
    )

    # Pessoas que apareceram nos outros 30 dias.
    outros_30_dias = set()

    for _, ids in aparicoes[2:]:

        outros_30_dias.update(
            ids
        )

    # Remove quem apareceu em qualquer dos outros 30 dias.
    prodigos = (
        candidatos
        - outros_30_dias
    )

    print(
        f"[PRÓDIGOS] Dia 1: "
        f"{dia_1.strftime('%d/%m/%Y')}"
    )

    print(
        f"[PRÓDIGOS] Dia 2: "
        f"{dia_2.strftime('%d/%m/%Y')}"
    )

    print(
        f"[PRÓDIGOS] Candidatos: "
        f"{len(candidatos)}"
    )

    print(
        f"[PRÓDIGOS] PRÓDIGOS encontrados: "
        f"{len(prodigos)}"
    )

    return (
        dia_1,
        dia_2,
        prodigos,
    )


# ============================================================
# OBTER MEMBRO
# ============================================================

async def obter_membro(
    guild,
    usuario_id,
):
    """
    Primeiro tenta pegar do cache.
    Se não encontrar, busca na API.
    """

    membro = guild.get_member(
        usuario_id
    )

    if membro is not None:
        return membro

    try:

        return await guild.fetch_member(
            usuario_id
        )

    except discord.NotFound:

        print(
            f"[PRÓDIGOS] Usuário {usuario_id} "
            f"não está mais no servidor."
        )

        return None

    except discord.HTTPException as e:

        print(
            f"[PRÓDIGOS] Erro ao buscar "
            f"{usuario_id}: {e}"
        )

        return None


# ============================================================
# ADICIONAR CARGO PRÓDIGOS
# ============================================================

async def adicionar_cargo_prodigos(
    membro,
    cargo,
):
    """
    Adiciona o cargo PRÓDIGOS caso o membro ainda
    não o possua.
    """

    if cargo is None:

        print(
            "[PRÓDIGOS] Cargo PRÓDIGOS não encontrado."
        )

        return False

    if cargo in membro.roles:

        print(
            f"[PRÓDIGOS] {membro} já possui "
            "o cargo PRÓDIGOS."
        )

        return True

    try:

        await membro.add_roles(
            cargo,
            reason=(
                "Usuário identificado como "
                "sem aparição nos últimos 30 dias."
            ),
        )

        print(
            f"[PRÓDIGOS] Cargo adicionado a "
            f"{membro} ({membro.id})."
        )

        return True

    except discord.Forbidden:

        print(
            f"[PRÓDIGOS] Sem permissão para adicionar "
            f"PRÓDIGOS a {membro} ({membro.id})."
        )

        return False

    except discord.HTTPException as e:

        print(
            f"[PRÓDIGOS] Erro ao adicionar cargo "
            f"a {membro} ({membro.id}): {e}"
        )

        return False


# ============================================================
# ENVIAR AVISO INDIVIDUAL
# ============================================================

async def enviar_aviso_prodigo(
    chat_logs,
    membro,
    ultima_aparicao,
):
    """
    Envia no chat_logs:

    ⚠️ Usuário sem aparição

    - Nome: ...
    - Apelido: ...
    - ID: `...`
    - Última aparição registrada: ...
    - Dias sem aparecer: ...
    """

    hoje = agora_brasilia().date()

    dias_sem_aparecer = (
        hoje - ultima_aparicao
    ).days

    mensagem = (
        "⚠️ **Usuário sem aparição**\n"
        f"- Nom {membro.name}\n"
        f"- Apelido: {membro.display_name}\n"
        f"- ID: `{membro.id}`\n"
        f"- Última aparição registrada: "
        f"{ultima_aparicao.strftime('%d/%m/%Y')}\n"
        f"- Dias sem aparecer: {dias_sem_aparecer}"
    )

    try:

        await chat_logs.send(
            mensagem
        )

    except discord.Forbidden:

        print(
            "[PRÓDIGOS] Sem permissão para enviar "
            "aviso no chat_logs."
        )

    except discord.HTTPException as e:

        print(
            f"[PRÓDIGOS] Erro ao enviar aviso: {e}"
        )


# ============================================================
# VERIFICAR DISCÍPULOS
# ============================================================

async def encontrar_discipulos(
    guild,
    prodigos,
):
    """
    Retorna somente os PRÓDIGOS que também possuem
    o cargo DISCÍPULOS.
    """

    cargo_discipulos = guild.get_role(
        CARGO_DISCIPULOS
    )

    if cargo_discipulos is None:

        print(
            "[PRÓDIGOS] Cargo DISCÍPULOS não encontrado."
        )

        return []

    membros = []

    for usuario_id in sorted(
        prodigos
    ):

        membro = await obter_membro(
            guild,
            usuario_id,
        )

        if membro is None:
            continue

        if cargo_discipulos in membro.roles:

            membros.append(
                membro
            )

    return membros


# ============================================================
# ENVIAR EMBED DOS DISCÍPULOS
# ============================================================

async def enviar_embed_discipulos(
    chat_logs,
    membros,
):
    """
    Envia uma embed com:
    - apelido;
    - ID.
    """

    if not membros:
        return

    embed = discord.Embed(
        title="PRÓDIGOS — DISCÍPULOS",
        description=(
            "Usuários identificados como PRÓDIGOS "
            "que também possuem o cargo DISCÍPULOS."
        ),
        timestamp=datetime.now(
            ZoneInfo("UTC")
        ),
    )

    linhas = []

    for membro in membros:

        linhas.append(
            f"**{membro.display_name}**\n"
            f"ID: `{membro.id}`"
        )

    # Discord permite até 1024 caracteres por campo.
    # Se houver muitos membros, dividimos em campos.

    blocos = []

    bloco_atual = []
    tamanho_atual = 0

    for linha in linhas:

        tamanho = len(linha) + 1

        if (
            tamanho_atual + tamanho
            > 1024
        ):

            blocos.append(
                "\n\n".join(
                    bloco_atual
                )
            )

            bloco_atual = []
            tamanho_atual = 0

        bloco_atual.append(
            linha
        )

        tamanho_atual += tamanho

    if bloco_atual:

        blocos.append(
            "\n\n".join(
                bloco_atual
            )
        )

    for indice, bloco in enumerate(
        blocos,
        start=1,
    ):

        nome_campo = (
            "Usuários"
            if len(blocos) == 1
            else f"Usuários {indice}"
        )

        embed.add_field(
            name=nome_campo,
            value=bloco,
            inline=False,
        )

    embed.set_footer(
        text=f"Total: {len(membros)}"
    )

    try:

        await chat_logs.send(
            embed=embed
        )

    except discord.Forbidden:

        print(
            "[PRÓDIGOS] Sem permissão para enviar "
            "a embed no chat_logs."
        )

    except discord.HTTPException as e:

        print(
            f"[PRÓDIGOS] Erro ao enviar embed: {e}"
        )


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

async def executar_verificacao_prodigos(
    bot,
    guild,
):
    """
    Executa a verificação completa.
    """

    print(
        "============================================================"
    )

    print(
        "[PRÓDIGOS] Iniciando verificação."
    )

    print(
        "============================================================"
    )

    # ========================================================
    # THREAD DE ÚLTIMAS APARIÇÕES
    # ========================================================

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
                f"[PRÓDIGOS] Não foi possível encontrar "
                f"a thread de últimas aparições: {e}"
            )

            return False

    # ========================================================
    # ÚLTIMAS 32 MENSAGENS
    # ========================================================

    aparicoes = await obter_32_aparicoes(
        thread
    )

    if aparicoes is None:
        return False

    # ========================================================
    # ENCONTRAR PRÓDIGOS
    # ========================================================

    (
        dia_1,
        dia_2,
        prodigos,
    ) = encontrar_prodigos(
        aparicoes
    )

    if not prodigos:

        print(
            "[PRÓDIGOS] Nenhum usuário encontrado."
        )

        return True

    # ========================================================
    # CHAT LOGS
    # ========================================================

    chat_logs = bot.get_channel(
        CHAT_LOGS
    )

    if chat_logs is None:

        try:

            chat_logs = await bot.fetch_channel(
                CHAT_LOGS
            )

        except Exception as e:

            print(
                f"[PRÓDIGOS] Não foi possível encontrar "
                f"chat_logs: {e}"
            )

            return False

    # ========================================================
    # CARGO PRÓDIGOS
    # ========================================================

    cargo_prodigos = guild.get_role(
        CARGO_PRODIGOS
    )

    if cargo_prodigos is None:

        print(
            f"[PRÓDIGOS] Cargo não encontrado: "
            f"{CARGO_PRODIGOS}"
        )

        return False

    # ========================================================
    # PROCESSAR CADA PRÓDIGO
    # ========================================================

    membros_processados = []

    for usuario_id in sorted(
        prodigos
    ):

        membro = await obter_membro(
            guild,
            usuario_id,
        )

        if membro is None:
            continue

        sucesso = await adicionar_cargo_prodigos(
            membro,
            cargo_prodigos,
        )

        if not sucesso:
            continue

        membros_processados.append(
            membro
        )

        # Se apareceu no dia 1, essa é a última aparição.
        #
        # Caso contrário, apareceu no dia 2.
        if usuario_id in aparicoes[0][1]:

            ultima_aparicao = dia_1

        else:

            ultima_aparicao = dia_2

        await enviar_aviso_prodigo(
            chat_logs,
            membro,
            ultima_aparicao,
        )

    # ========================================================
    # VERIFICAR DISCÍPULOS
    # ========================================================

    membros_discipulos = (
        await encontrar_discipulos(
            guild,
            prodigos,
        )
    )

    if membros_discipulos:

        await enviar_embed_discipulos(
            chat_logs,
            membros_discipulos,
        )

    # ========================================================
    # FINAL
    # ========================================================

    print(
        f"[PRÓDIGOS] Concluído."
    )

    print(
        f"[PRÓDIGOS] Encontrados: "
        f"{len(prodigos)}"
    )

    print(
        f"[PRÓDIGOS] Processados: "
        f"{len(membros_processados)}"
    )

    print(
        f"[PRÓDIGOS] Discípulos: "
        f"{len(membros_discipulos)}"
    )

    return True


# ============================================================
# SLASH COMMAND
# ============================================================

def registrar_comando_prodigos(
    bot,
    cargo_administrador,
    cargo_focus_adm,
):
    """
    Registra:

        /prodigos verificar
    """

    grupo = app_commands.Group(
        name="prodigos",
        description="Comandos relacionados aos PRÓDIGOS."
    )

    @grupo.command(
        name="verificar",
        description="Verifica os PRÓDIGOS."
    )
    async def verificar_prodigos(
        interaction: discord.Interaction
    ):

        # ----------------------------------------------------
        # SERVIDOR
        # ----------------------------------------------------

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado no servidor.",
                ephemeral=True,
            )

            return

        # ----------------------------------------------------
        # MEMBRO
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # PERMISSÃO
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # RESPONDER IMEDIATAMENTE
        # ----------------------------------------------------

        await interaction.response.send_message(
            "⏳ Iniciando a verificação dos PRÓDIGOS...",
            ephemeral=True,
        )

        # ----------------------------------------------------
        # EXECUTAR
        # ----------------------------------------------------

        sucesso = await executar_verificacao_prodigos(
            bot,
            interaction.guild,
        )

        if sucesso:

            await interaction.edit_original_response(
                content=(
                    "✅ Verificação dos PRÓDIGOS concluída."
                )
            )

        else:

            await interaction.edit_original_response(
                content=(
                    "❌ A verificação dos PRÓDIGOS "
                    "não pôde ser concluída."
                )
            )

    bot.tree.add_command(
        grupo
    )


# ============================================================
# TAREFA AUTOMÁTICA — 00:05
# ============================================================

async def tarefa_prodigos(
    bot,
):
    """
    Executa automaticamente todos os dias às 00:05
    no horário de Brasília.
    """

    global _ultima_execucao_automatica

    await bot.wait_until_ready()

    while not bot.is_closed():

        try:

            agora = agora_brasilia()

            # ------------------------------------------------
            # CALCULAR PRÓXIMA EXECUÇÃO
            # ------------------------------------------------

            proxima_execucao = datetime(
                agora.year,
                agora.month,
                agora.day,
                0,
                5,
                0,
                0,
                tzinfo=FUSO_BRASILIA,
            )

            if agora >= proxima_execucao:

                proxima_execucao += timedelta(
                    days=1
                )

            segundos = (
                proxima_execucao - agora
            ).total_seconds()

            print(
                f"[PRÓDIGOS] Próxima execução automática "
                f"em aproximadamente "
                f"{segundos:.0f} segundos."
            )

            await asyncio.sleep(
                max(
                    segundos,
                    1
                )
            )

            # ------------------------------------------------
            # VERIFICAR DATA
            # ------------------------------------------------

            agora = agora_brasilia()

            data_execucao = agora.date()

            if (
                _ultima_execucao_automatica
                == data_execucao
            ):

                continue

            _ultima_execucao_automatica = (
                data_execucao
            )

            print(
                "[PRÓDIGOS] 00:05 atingido. "
                "Iniciando verificação automática."
            )

            # ------------------------------------------------
            # SERVIDORES
            # ------------------------------------------------

            for guild in bot.guilds:

                try:

                    await executar_verificacao_prodigos(
                        bot,
                        guild,
                    )

                except Exception as e:

                    print(
                        f"[PRÓDIGOS] Erro ao processar "
                        f"servidor {guild.id}: {e}"
                    )

        except asyncio.CancelledError:

            print(
                "[PRÓDIGOS] Tarefa automática cancelada."
            )

            raise

        except Exception as e:

            print(
                f"[PRÓDIGOS] Erro na tarefa automática: {e}"
            )

            await asyncio.sleep(10)


# ============================================================
# INICIAR TAREFA
# ============================================================

def iniciar_tarefa_prodigos(
    bot,
):

    global _tarefa_prodigos

    if (
        _tarefa_prodigos is None
        or _tarefa_prodigos.done()
    ):

        _tarefa_prodigos = asyncio.create_task(
            tarefa_prodigos(
                bot
            )
        )

    return _tarefa_prodigos