import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import get
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
import os
import json
import asyncio
import re
import time
import io
import subprocess
from discord.ext import tasks
from zoneinfo import ZoneInfo
from datetime import time, datetime, timezone, timedelta
from collections import defaultdict
from config import TOKEN

from google import genai
from google.genai import types
from gemini_manager import proxima_api, marcar_api_como_indisponivel


bot = commands.Bot(command_prefix=";", intents=intents, help_command=None)

#region ---- 🆔 IDs

#region 💬 CHATS E THREADS
chat_convites = 1347727627104030747
chat_ticket = 1517166503584202965 #atualmente é o chat "regras" (06/09/2026)
chat_ticket_apolo = 1520967600417542244
chat_registro = 1435803255060955136
chat_punicoes = 1385423723796107395
chat_logs = 1523110468124803204
chat_logs_thread_motivos = 1524822398149595316
chat_logs_thread_fotos = 1539444442489032756
chat_logs_thread_boosters = 1539463668310483005
chat_logs_threads_apelidos_DDD = 1542351873938300928
chat_logs_thread_analise_de_imagens = 1549257351285182604
chat_conversas = 1347727626910826550
chat_mensagem_do_dia = 1455697665772748810
chat_thread_ddd_logs = 1545924442666835978
chat_thread_agendar_msgs = 1546375907181338754
chat_thread_passar_direto = 1549406253606895696
#endregion

#region 📞 CALLS
eden = 1437623938166558782
getsemani = 1432201092778819767
sinai = 1461791125902725283
oliveiras = 1538199427393527828
jaco = 1414045262783053924
laai_roi = 1537998563659874404
salmos = 1538198570900131860
canticos = 1538204120073248768
#endregion

#region 👤PESSOAS E BOTS
invite_tracker_bot = 720351927581278219
#endregion

#region 👥👥 CARGOS
valentes = 1347727626512367724
cargo_moderador = 1347727626558636149
cargo_administrador = 1347727626558636150
cargo_focus_adm = 1542008291897511966
cargo_pedir_acesso = 1517346084895195236
cargo_ver_chat_explicacao = 1523156945287250053
a_verificar = 1485807461863788584
cargo_verificado = 1485807343793868931
cargo_conta_suspeita = 1457175374772568177
cargo_homem = 1357189618281349240
cargo_mulher = 1357189666633289750
cargo_genero_nao_informado = 1457117094465376389
cargo_recepcionista = 1419489233940512828
cargo_sem_acesso = 1496681162825928704
cargo_booster = 1466245562138624177
cargo_destaque_do_dia = 1453468077084905627
conquista_a_fundacao = 1446897806735314987
ping_staff = 1385429423754444882
cargo_CC = 1447060338242490561
cargo_membro = 1347727626525216902
cargo_divisoria_caracteristicas = 1347727626512367719
cargo_divisoria_conquistas = 1357876891322814616
cargo_divisoria_pings = 1347727626512367725
cargo_tempo = 1518666285406359743
#endregion

#region 👥⛪ cargos de religião
nao_cristao = 1357191197374025788
catolicos = [
    1357191788389204079, #católico
    1363231111731482704 #ortodoxo
]
neopentecostal = 1449955047558353038
protestante = 1357191419906887821
pentecostais = [
    1363232583818809535, #pentecostal
    1357191257771741186, #assembleiano
    1488691820090359908, #IPDA
]
batista = 1357191349736308888
presbiteriano = 1357191536311533580
adventista = 1357191593970372648
ccb = 1360779400601276456
luterano = 1386438595442770033
metodista = 1376018322348310569
anglicano = 1449955091229446257
nao_denominacional = 1363226771926814913
outra_denominacao = 1357191650094612641
outros_protestantes = [
    pentecostais,
    batista,
    presbiteriano,
    adventista,
    luterano,
    metodista,
    anglicano,
    ccb
]
#endregion
#endregion

#region ------- 🗂️ Em outras pastas...
#region---------------------------- slash
#region 📞👥cargo_call
from comandos.slash.cargo_call import registrar_comando_cargo_call
registrar_comando_cargo_call(
    bot,
    valentes,
    chat_logs
)
#endregion
#region 📴desligar_focus
from comandos.slash.desligar_focus import registrar_comando_desligar_focus
registrar_comando_desligar_focus(
    bot,
    chat_logs,
    cargo_focus_adm,
    cargo_administrador
)
#endregion
#region 👥👥adicionar_cargo_em_massa
from comandos.slash.adicionar_cargo_em_massa import (
    registrar_comando_adicionar_cargo_em_massa
)
registrar_comando_adicionar_cargo_em_massa(
    bot,
    cargo_focus_adm,
    cargo_administrador,
    chat_logs
)
#endregion
#region ⭐mensagem do dia (ping)
from comandos.slash.mensagem_do_dia import (
    registrar_comando_mensagem_do_dia
)
registrar_comando_mensagem_do_dia(
    bot,
    cargo_focus_adm,
    cargo_administrador,
    chat_mensagem_do_dia,
    chat_logs
)
#endregion
#endregion
#region---------------------------- events
#region ⭐destaque_do_dia
from comandos.events.destaque_do_dia import verificar_destaque_do_dia
#endregion
#region 💬criar_topico_privado_ao_perder_pedir_acesso
from comandos.events.topico_privado_automatico import (
    criar_topico_privado_automatico
)
#o código continua na parte do on_member_update, no "if" de perder pedir_acesso. Atualmente isso é na linha 1470.
#endregion
#region 📅agendar_mensagens
from comandos.events.agendar_mensagens import iniciar_agendador
agendador_mensagens_task = None
#continua no on_ready
#endregion
#region 🖼️análise de imagens
from comandos.events.analise_de_imagens import (
    analisar_mensagem_de_imagem
)
#endregion
#region 🔵sapphire threads, apagar
from comandos.events.sapphire_thread import (
    on_thread_create,
    verificar_thread_sapphire
)
bot.add_listener(on_thread_create, "on_thread_create")
#endregion
#region 👤 aparicoes diarias
from comandos.events.aparicoes_diarias import (
    registrar_aparicoes_diarias,
    iniciar_tarefa_aparicoes_diarias
)

registrar_aparicoes_diarias(
    bot,
    cargo_administrador,
    cargo_focus_adm
)

aparicoes_diarias_task = None
#endregion
#region Pródigos
from comandos.events.prodigos import (
    registrar_comando_prodigos,
    iniciar_tarefa_prodigos,
)

registrar_comando_prodigos(
    bot,
    cargo_administrador,
    cargo_focus_adm,
)
#endregion
#endregion
#endregion
#endregion

#region Comando ;ping
@bot.command()
async def ping(ctx):
    await ctx.send("""Pong!
-# Focus v2""")
#endregion
#region Comando ;help
@bot.command()
async def help(ctx):
    await ctx.send("Não tem comando de help.")
#endregion
#region Comando ;ração
@bot.command()
async def ração(ctx):
    await ctx.send("https://klipy.com/gifs/cat-1282")
#endregion
#region Comando ;gosminha
@bot.command()
async def gosminha(ctx):
    await ctx.send("https://tenor.com/view/black-slime-stim-oddly-satisfying-gif-gif-12598525")
    #endregion
#region /mensagem_pv
# Mensagens prontas
MENSAGENS = {
    "teste": "Apenas um teste.",
    "advertencia": "Olá! Esta é uma advertência. Pedimos que leia novamente as regras do servidor.",
    "foto1": "Sua foto infringe as regras do servidor, pedimos que troque.",
    "foto2": """⚠️ **Advertência**

Esta advertência refere-se à sua foto de perfil anterior, que continha a imagem de uma mulher seminua (independentemente de ser você ou não), o que não é permitido em nosso servidor.

Percebemos que a foto já foi alterada, o que resolve a situação. Ainda assim, esta advertência será registrada como orientação para que esse tipo de imagem não seja utilizado novamente.

Em nosso servidor, solicitamos que fotos de perfil sejam compatíveis com a proposta cristã da comunidade. Em caso de reincidência, poderão ser aplicadas medidas de moderação mais severas.
    """
}

@bot.tree.command(name="mensagem_pv", description="Envia uma mensagem no privado de um usuário.")
@app_commands.describe(
    usuario="Usuário que receberá a mensagem",
    predefinida="Escolha uma mensagem pronta",
    mensagem="Escreva uma mensagem personalizada"
)
@app_commands.choices(
    predefinida=[
        app_commands.Choice(name="Teste", value="teste"),
        app_commands.Choice(name="Advertência", value="advertencia"),
        app_commands.Choice(name="foto1", value="foto1"),
        app_commands.Choice(name="foto2", value="foto2")
    ]
)
async def mensagem(
    interaction: discord.Interaction,
    usuario: discord.Member,
    predefinida: app_commands.Choice[str] = None,
    mensagem: str = None
):

    if cargo_moderador not in [cargo.id for cargo in interaction.user.roles]:
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
          ephemeral=True
        )
        return

    # Usa a mensagem personalizada caso exista
    if mensagem:
        texto = mensagem
    elif predefinida:
        texto = MENSAGENS[predefinida.value]
    else:
        await interaction.response.send_message(
            "Você precisa informar uma mensagem personalizada ou escolher uma mensagem predefinida.",
            ephemeral=True
        )
        return

    if usuario == bot.user:
        await interaction.response.send_message(
            "❌ Não é possível enviar uma mensagem privada para o próprio bot.",
            ephemeral=True
        )
        return
    try:
        await usuario.send(texto)
    except discord.Forbidden:
        await interaction.response.send_message(
            "Não foi possível enviar mensagem para esse usuário.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"✅ Mensagem privada enviada para {usuario.mention}.\n"
        f"-# Evite enviar muitas mensagens em pouco tempo.",
        ephemeral=True
    )

    canal_logs = interaction.guild.get_channel(chat_logs)

    if canal_logs:
        embed = discord.Embed(
            title="📨 Mensagem privada enviada",
            color=discord.Color.yellow()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_author(
            name=f"Enviado por {interaction.user}",
            icon_url=interaction.user.display_avatar
        )
        embed.add_field(
            name="Enviado por",
            value=f"{interaction.user.mention}\n`{interaction.user.id}`",
            inline=False
        )
        embed.add_field(
            name="Destinatário",
            value=f"{usuario.mention}\n`{usuario.id}`",
            inline=False
        )
        embed.add_field(
            name="Mensagem",
            value=f"```{texto}```",
            inline=False
        )
        await canal_logs.send(embed=embed)
#endregion
#region Comando ;jeftoide
@bot.command()
async def jeftoide(ctx):
    result_js = subprocess.run(
        ["node", "./js/script.js"],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )

    data = json.loads(result_js.stdout)

    await ctx.send(data["message"])
#endregion


#region -------------- ;chat
# EMBED
def embed_chat(usuario: discord.Member):

    embed = discord.Embed(
        title="Boas-vindas! É uma alegria ter você conosco.",
        description=(
            "Nosso objetivo é que este servidor seja um espaço de **comunhão** e **crescimento** na sua caminhada com Cristo. Embora nossa base teológica seja **protestante**, nossas portas estão abertas para todos que buscam aprender mais sobre Deus. Você pode se apresentar em <#1363009444111188129>."
        ),
        color=discord.Color.blue()
    )
    # Foto de perfil da pessoa no canto superior direito
    embed.set_thumbnail(url=usuario.display_avatar.url)
    # Imagem grande na parte inferior
    embed.set_image(url="https://i.imgur.com/Xwjxew6.jpg")
    embed.set_footer(text="Bíblia em Foco")
    return embed


# PROCURAR TÓPICO
async def procurar_topico(
    guild: discord.Guild,
    usuario: discord.Member
):
    canal = guild.get_channel(chat_conversas)

    if canal is None:
        return None

    usuario_id = str(usuario.id)

    # THREADS ATIVAS
    for thread in canal.threads:
        if usuario_id in thread.name:
            return thread

    # THREADS PRIVADAS ARQUIVADAS
    async for thread in canal.archived_threads(limit=None):
        if usuario_id in thread.name:

            # Desarquiva caso esteja arquivada
            if thread.archived:
                await thread.edit(archived=False)

            return thread

    return None

# REGISTRAR LOG
async def registrar_log(
    guild: discord.Guild,
    titulo: str,
    descricao: str,
    cor=discord.Color.blurple()
):
    canal = guild.get_channel(chat_logs)
    if canal is None:
        return
    embed = discord.Embed(
        title=titulo,
        description=descricao,
        color=cor
    )
    await canal.send(embed=embed)

# CRIAR TÓPICO
async def criar_topico(
    guild: discord.Guild,
    usuario: discord.Member,
    moderador: discord.Member | None = None
):

    canal = guild.get_channel(chat_conversas)

    titulo = f"{usuario.display_name} | {usuario.id}"

    thread = await canal.create_thread(
        name=titulo,
        type=discord.ChannelType.private_thread,
        invitable=False,
        auto_archive_duration=60
    )

    # envia a mensagem inicial
    await thread.send("Criando chat...")

    # envia embed
    await thread.send(
        embed=embed_chat(usuario)
    )

    # marca o dono
    await thread.send(usuario.mention)

    # se for moderador, marca também
    if moderador is not None:
        await thread.send(moderador.mention)

    descricao = (
        f"**Usuário:** {usuario} ({usuario.id})\n"
        f"**Tópico:** {thread.mention}\n"
        f"**Link:** {thread.jump_url}"
    )

    if moderador:
        descricao += (
            f"\n**Solicitado por:** "
            f"{moderador} ({moderador.id})"
        )

    await registrar_log(
        guild,
        "🆕 Chat criado",
        descricao,
        discord.Color.green()
    )

    return thread
# OBTER OU CRIAR
async def obter_ou_criar_chat(
    guild: discord.Guild,
    usuario: discord.Member,
    moderador: discord.Member | None = None
):

    thread = await procurar_topico(guild, usuario)
    # já existe
    if thread:

        descricao = (
            f"**Usuário:** {usuario} ({usuario.id})\n"
            f"**Tópico:** {thread.mention}\n"
            f"**Link:** {thread.jump_url}"
        )
        if moderador:
            descricao += (
                f"\n**Solicitado por:** "
                f"{moderador} ({moderador.id})"
            )
            # marca o moderador
            await thread.send(embed=embed_chat())
            await thread.send(moderador.mention)

        else:

            await thread.send(embed=embed_chat())
            await thread.send(usuario.mention)

        await registrar_log(
            guild,
            "📂 Chat localizado",
            descricao,
            discord.Color.gold()
        )

        return thread
    # cria novo

    return await criar_topico(
        guild,
        usuario,
        moderador
    )

# VERIFICAR PERMISSÃO

def eh_staff(membro: discord.Member):

    cargos = {
        cargo_moderador,
        cargo_administrador
    }

    return any(
        cargo.id in cargos
        for cargo in membro.roles
    )

# COMANDO ;chat ===========================================================
@bot.command(name="chat")
async def chat(ctx, argumento=None):
    # VERIFICAR SE O COMANDO FOI USADO EM UM SERVIDOR
    if ctx.guild is None:
        await ctx.reply(
            "❌ Este comando só pode ser usado em um servidor.",
            mention_author=False
        )
        return

    # CASO 1: ;chat
    if argumento is None:
        usuario = ctx.author
        # Procurar o chat dessa pessoa
        thread = await procurar_topico(
            ctx.guild,
            usuario
        )
        # CHAT JÁ EXISTE:
        if thread is not None:
            # Envia a embed
            #await thread.send(
            #    embed=embed_chat(usuario)
            #)
            # A menção precisa ser uma mensagem normal
            await thread.send(
                usuario.mention
            )
            # Responder ao comando com o link
            await ctx.reply(
                f"Seu chat: {thread.jump_url}",
                mention_author=False
            )
            # Registrar no log
            await registrar_log(
                ctx.guild,
                "📂 Chat localizado",
                (
                    f"**Dono do chat:** "
                    f"{usuario} (`{usuario.id}`)\n"
                    f"**Tópico:** {thread.name}\n"
                    f"**Link:** {thread.jump_url}\n"
                    f"**Comando usado por:** "
                    f"{ctx.author} (`{ctx.author.id}`)"
                ),
                discord.Color.gold()
            )

            return

        # CHAT NÃO EXISTE
        thread = await criar_topico(
            ctx.guild,
            usuario
        )
        # Responder ao comando com o link
        await ctx.reply(
            f"Seu chat: {thread.jump_url}",
            mention_author=False
        )
        return

    # CASO 2: ;chat @usuário / ;chat ID
    usuario = None
    # Tentar encontrar por menção
    if ctx.message.mentions:
        usuario = ctx.message.mentions[0]
    # Se não houver menção, tentar encontrar pelo ID
    else:
        try:
            usuario_id = int(argumento)
        except ValueError:
            await ctx.reply(
                "❌ Você precisa mencionar um usuário ou informar um ID válido.",
                mention_author=False
            )
            return

        usuario = ctx.guild.get_member(usuario_id)

        # Se o membro não estiver no cache, buscar pela API
        if usuario is None:
            try:
                usuario = await ctx.guild.fetch_member(
                    usuario_id
                )

            except discord.NotFound:
                await ctx.reply(
                    "❌ Não encontrei esse membro no servidor.",
                    mention_author=False
                )
                return

            except discord.HTTPException:

                await ctx.reply(
                    "❌ Não foi possível encontrar esse membro.",
                    mention_author=False
                )
                return

    # VERIFICAR PERMISSÃO
    if not eh_staff(ctx.author):
        await ctx.reply(
            "❌ Você não tem permissão para abrir o chat de outra pessoa.",
            mention_author=False
        )
        return

    #region limitação do A Fundação
    # VERIFICAR PERMISSÃO ESPECIAL DA CONQUISTA À FUNDAÇÃO
    cargo_conquista = ctx.guild.get_role(conquista_a_fundacao)

    if cargo_conquista is not None:
        # Se a pessoa do chat possui o cargo...
        if cargo_conquista in usuario.roles:

            # ...o moderador também precisa possuir o cargo
            if cargo_conquista not in ctx.author.roles:
                await ctx.reply(
                    "❌ Você não tem permissão para abrir o chat desta pessoa.",
                    mention_author=False
                )
                return
    #endregion


    # PROCURAR CHAT DO USUÁRIO INFORMADO
    thread = await procurar_topico(
        ctx.guild,
        usuario
    )
    # CHAT JÁ EXISTE
    if thread is not None:
        # Envia a embed usando o avatar do dono do chat
        #await thread.send(
        #    embed=embed_chat(usuario)
        #)
        # IMPORTANTE:
        # Se o chat já existia, marca quem executou o comando, e NÃO o dono do chat.
        await thread.send(
            ctx.author.mention
        )
        # Responder ao comando
        await ctx.reply(
            f"Chat de {usuario.mention}: {thread.jump_url}",
            mention_author=False
        )
        # Registrar no log
        await registrar_log(
            ctx.guild,
            "📂 Chat localizado",
            (
                f"**Dono do chat:** "
                f"{usuario} (`{usuario.id}`)\n"
                f"**Tópico:** {thread.name}\n"
                f"**Link:** {thread.jump_url}\n"
                f"**Solicitado por:** "
                f"{ctx.author} (`{ctx.author.id}`)"
            ),
            discord.Color.gold()
        )
        return

    #CHAT NAO EXISTE
    thread = await criar_topico(
        ctx.guild,
        usuario,
        moderador=ctx.author
    )

    # Responder ao comando
    await ctx.reply(
        f"Chat de {usuario.mention}: {thread.jump_url}",
        mention_author=False
    )
#endregion


#region comando ;r ou ;registro
@bot.command(aliases=["r"])
async def registro(ctx, user_id: str):
    if cargo_moderador not in [role.id for role in ctx.author.roles]:
        return
    forum = bot.get_channel(chat_registro)

    if forum is None:
        await ctx.reply("Não encontrei o fórum de registros.")
        return

    encontrados = []

    # Threads ativas
    for thread in forum.threads:
        if user_id in thread.name:
            encontrados.append(thread)

    # Threads arquivadas
    async for thread in forum.archived_threads(limit=None):
        if user_id in thread.name:
            encontrados.append(thread)

    if not encontrados:
        await ctx.reply("Nenhum registro encontrado para esse ID.")
        return

    links = "\n".join(thread.jump_url for thread in encontrados)

    await ctx.reply(
        f"Encontrei {len(encontrados)} registro(s):\n{links}",
        mention_author=False
    )
#endregion
#region comando ;rm ou ;registrom
@bot.command(aliases=["rm"])
async def registrom(ctx, user_id: str):
    if cargo_moderador not in [role.id for role in ctx.author.roles]:
        return
    forum = bot.get_channel(chat_registro)

    if forum is None:
        return

    encontrados = []

    # Threads ativas
    for thread in forum.threads:
        if user_id in thread.name:
            encontrados.append(thread)

    # Threads arquivadas
    async for thread in forum.archived_threads(limit=None):
        if user_id in thread.name:
            encontrados.append(thread)

    # Apaga a mensagem do comando
    try:
        await ctx.message.delete()
    except:
        pass

    if not encontrados:
        msg = await ctx.send("Nenhum registro encontrado.")
        await asyncio.sleep(7)
        await msg.delete()
        return

    # Quem usou o comando
    autor = ctx.author

    for thread in encontrados:
        try:
            mensagem = await thread.send(autor.mention)
            await asyncio.sleep(7)
            await mensagem.delete()
        except:
            pass
#endregion

#region comando ;m ou ;mensagem
@bot.command(aliases=["m"])
@commands.has_permissions(manage_messages=True)  # Opcional
async def mensagem(ctx, *, texto=None):
    if not any(role.id in (cargo_moderador, cargo_recepcionista) for role in ctx.author.roles):
        return
    if texto is None:
        await ctx.reply("Uso: `;m [id_do_chat ou #canal] mensagem`")
        return

    canal_destino = ctx.channel
    mensagem = texto

    partes = texto.split(maxsplit=1)

    if partes:
        primeiro = partes[0]

        # Caso seja um ID de canal
        if primeiro.isdigit():
            canal = bot.get_channel(int(primeiro))
            if canal:
                canal_destino = canal
                mensagem = partes[1] if len(partes) > 1 else ""

        # Caso seja uma menção de canal (<#id>)
        else:
            match = re.match(r"<#(\d+)>", primeiro)
            if match:
                canal = bot.get_channel(int(match.group(1)))
                if canal:
                    canal_destino = canal
                    mensagem = partes[1] if len(partes) > 1 else ""

    if not mensagem.strip():
        await ctx.reply("Você não informou a mensagem.")
        return

    # Envia a mensagem
    await canal_destino.send(mensagem)

    # Registra nos logs
    canal_logs = bot.get_channel(chat_logs)
    if canal_logs:
        await canal_logs.send(
            f"📨 **Mensagem enviada pelo comando ;m**\n"
            f"**Autor:** {ctx.author} ({ctx.author.id})\n"
            f"**Canal de origem:** {ctx.channel.mention} ({ctx.channel.id})\n"
            f"**Canal de destino:** {canal_destino.mention} ({canal_destino.id})\n"
            f"**Mensagem:**\n```{mensagem}```"
        )

    # Apaga a mensagem do comando
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    except discord.HTTPException:
        pass
#endregion

#region Dizer que ligou
PASTA_BOT = os.path.basename(os.path.dirname(__file__))

@bot.event
async def on_ready():

    global agendador_mensagens_task

    await bot.tree.sync()

    print(f"Logado como {bot.user}")

    channel = bot.get_channel(chat_logs)

    if channel is not None:
        await channel.send(
            f"""🟢 "E foi feito alma vivente".
-# 📁 `{PASTA_BOT}`"""
        )

    await verificar_thread_sapphire(bot)

    # ============================================================
    # AGENDADOR DE MENSAGENS
    # ============================================================

    if (
        agendador_mensagens_task is None
        or agendador_mensagens_task.done()
    ):

        agendador_mensagens_task = asyncio.create_task(
            iniciar_agendador(
                bot,
                chat_thread_agendar_msgs,
                chat_conversas,
                chat_logs
            )
        )

    #region APARIÇÕES DIÁRIAS ------------

    global aparicoes_diarias_task
    if (
        aparicoes_diarias_task is None
        or aparicoes_diarias_task.done()
    ):
        aparicoes_diarias_task = iniciar_tarefa_aparicoes_diarias(
            bot
        )
    #endregion

    #region Pródigos
    iniciar_tarefa_prodigos(bot)
    #endregion
#endregion

#region ---------- Pingar em novas threads (novo fórum) -------------------
#region Definir
canais_ping_novo_forum = [
    1387612050917953676, #pedidos de oracao
    1432187527447711825, #pregações
    1417906970706579599, #leitura diária
    1367167818117681305, #dúvidas
    1353534352474247168, #temas gerais
    1387978457635356693, #debates
    1517362589385097326, #artes
    1347727626910826554, #divulgação
    1440861614025740308, #louvores
]
canal_apresentacoes = 1363009444111188129
cargo_apresentado = 1455035687156973788
#endregion
@bot.event
async def on_thread_create(thread: discord.Thread):
    #region Detectar Threads
    await asyncio.sleep(1)

    if thread.parent is None:
        return

    if not isinstance(thread.parent, discord.ForumChannel):
        return

    autor = thread.owner

    # Caso owner ainda não esteja disponível
    if autor is None:
        try:
            autor = await bot.fetch_user(thread.owner_id)
        except:
            autor = None

    canal_logs = bot.get_channel(chat_logs)
    #endregion
    #region Marcar Ping Novo Fórum
    if thread.parent.id in canais_ping_novo_forum:

        msg = await thread.send(
            "<@&1455326865446408315>"
        )

        await asyncio.sleep(7)
        await msg.delete()

        if canal_logs:
            embed = discord.Embed(
                title="🆕 Novo tópico criado",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Criado por",
                value=f"{autor.mention if autor else 'Desconhecido'}",
                inline=False
            )
            embed.add_field(
                name="Canal",
                value=thread.parent.mention,
                inline=False
            )
            embed.add_field(
                name="Tópico",
                value=f"[Clique aqui]({thread.jump_url})",
                inline=False
            )
            embed.add_field(
                name="Ação",
                value="Mensagem temporária enviada e apagada após 7 segundos.",
                inline=False
            )
            await canal_logs.send(embed=embed)
        return
    #endregion
    #region Marcar Ping Recepcionistas
    if thread.parent.id == canal_apresentacoes:

        await thread.send(
            "<@&1555543123638231120>"
        )

        membro = thread.guild.get_member(thread.owner_id)

        if membro:
            cargo = thread.guild.get_role(cargo_apresentado)

            if cargo:
                await membro.add_roles(
                    cargo,
                    reason="Criou uma apresentação."
                )

        if canal_logs:
            embed = discord.Embed(
                title="👋 Nova apresentação",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Criado por",
                value=f"{autor.mention if autor else 'Desconhecido'}",
                inline=False
            )
            embed.add_field(
                name="Canal",
                value=thread.parent.mention,
                inline=False
            )
            embed.add_field(
                name="Tópico",
                value=f"[Clique aqui]({thread.jump_url})",
                inline=False
            )
            embed.add_field(
                name="Ações",
                value=(
                    "• Mensagem enviada no tópico.\n"
                    "• Cargo de apresentado concedido."
                ),
                inline=False
            )
            await canal_logs.send(embed=embed)
            #endregion
#endregion

#region --------------- Evento: Quando o membro entrar
@bot.event
async def on_member_join(membro: discord.Member):
#region Criar tópico no chat de convites
    await asyncio.sleep(4)

    canal = membro.guild.get_channel(chat_convites)
    if canal is None:
        return

    agora = datetime.now(timezone.utc)
    dias = (agora - membro.created_at).days

    mensagem_base = None
    ultima_mensagem_bot = None

    # Procura a mensagem do Invite Tracker Bot
    async for msg in canal.history(limit=20):

        if msg.author.id != invite_tracker_bot:
            continue

        if ultima_mensagem_bot is None:
            ultima_mensagem_bot = msg

        idade = (agora - msg.created_at).total_seconds()

        if idade <= 10:
            conteudo = msg.content.lower()

            if (
                str(membro.id) in conteudo
                or membro.name.lower() in conteudo
                or membro.display_name.lower() in conteudo
            ):
                mensagem_base = msg
                break

    if mensagem_base is None:
        mensagem_base = ultima_mensagem_bot

    if mensagem_base is None:
        return

    # Criação do tópico

    try:
        thread = await mensagem_base.create_thread(
            name=f"{membro.name} {membro.id}",
            auto_archive_duration=60
        )

    except discord.HTTPException:

        thread = await canal.create_thread(
            name=f"{membro.name} {membro.id}",
            type=discord.ChannelType.public_thread,
            auto_archive_duration=60
        )

    # Primeira mensagem

    fluxograma_recepcao = "https://cdn.discordapp.com/attachments/1522709780051923214/1529144496196161576/image.png?ex=6a6775ca&is=6a66244a&hm=9eee175b33ddcb8b755184bf4ad39aa7665cd72accf65c7b1a2330b13e6a117c"
    await thread.send(fluxograma_recepcao)    
    await thread.send("<@&1419489233940512828>") #ping de recepcionistas. o yagpdb apaga.
    
    if dias < 1:
        idade = "Menos de 1 dia \n VERIFICAÇÃO OBRIGATÓRIA"
    elif dias == 1:
        idade = "**1 dias \n VERIFICAÇÃO OBRIGATÓRIA"
    elif dias <14:
        idade = f"{dias} dias \n VERIFICAÇÃO OBRIGATÓRIA"
    elif dias < 30:
        idade = f"**{dias} dias**"
    elif dias < 365:
        meses = dias // 30
        idade = f"{meses} mês" if meses == 1 else f"{meses} meses"
    else:
        anos = dias // 365
        idade = f"{anos} ano" if anos == 1 else f"{anos} anos"


    embed = discord.Embed(
        title="Novo membro",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.add_field(
        name="Nome",
        value=membro.name,
        inline=False
    )
    embed.add_field(
            name="Menção",
            value=membro.mention,
            inline=True
    )
    embed.add_field(
        name="ID",
        value=str(membro.id),
        inline=False
    )
    embed.add_field(
        name="Idade da conta",
        value=idade,
        inline=False
    )
    embed.add_field(
        name="Verifique o xp global com a Loritta",
        value="Se for menor que **3000**, verificação obrigatória.",
        inline=False
    )
    await thread.send(
        content=f"{membro.mention}",
        embed=embed
    )
    id_usuario = membro.id
    await asyncio.sleep(1)
    await thread.send(f"Verifique o **xp** na loritta: \n ```+perfil {id_usuario}```")
    await thread.send(f"+perfil {id_usuario}")
    await asyncio.sleep(5)
    await thread.send(f"Verifique o **perfil** do discord: \n# {membro.mention}")

    # Procura o ID apenas no chat_convites
    # (ignora mensagens do dia atual)
    inicio_hoje = datetime.now(timezone.utc).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    encontrou = False
    async for msg in canal.history(limit=None, before=inicio_hoje):

        if str(membro.id) in msg.content:
            encontrou = True
            break

    if encontrou:
        await thread.send(
            "⚠️ Achei o ID dessa pessoa anteriormente no chat de convites."
        )
    else:
        await thread.send(
            "✅ Nenhuma ocorrência anterior desse ID foi encontrada."
        )
    #endregion

#endregion

#region passar direto
# region --------------- PASSAGEM DIRETA

async def membro_esta_na_thread_passar_direto(membro: discord.Member):
    """
    Verifica se o ID do membro está registrado na thread
    chat_thread_passar_direto.

    Retorna:
        True  -> ID encontrado
        False -> ID não encontrado ou erro
    """

    try:
        thread = bot.get_channel(chat_thread_passar_direto)

        if thread is None:
            thread = await bot.fetch_channel(chat_thread_passar_direto)

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
#endregion
#endregion

#region --------------- ticket de entrada
async def criar_ticket_entrada(membro: discord.Member):
    role = discord.utils.get(membro.guild.roles, id=cargo_ver_chat_explicacao)

    if role:
        await asyncio.sleep(2)
        await membro.remove_roles(role)

    channel = bot.get_channel(chat_ticket)

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
#endregion
#region Manualmente:
@bot.tree.command(
    name="criar_ticket",
    description="Cria manualmente o ticket de entrada de um membro."
)
@app_commands.describe(
    usuario="Membro que receberá o ticket"
)
async def criar_ticket(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    if cargo_moderador not in [cargo.id for cargo in interaction.user.roles]:
        await interaction.response.send_message(
            "❌ Você não tem permissão.",
            ephemeral=True
        )
        return

    await criar_ticket_entrada(usuario)

    await interaction.response.send_message(
        f"✅ Ticket criado para {usuario.mention}.",
        ephemeral=True
    )
#endregion
#region Evento: on_member_update - Acontece ao membro entrar e responder ao onboarding

# procurar tópico
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

#region FOTO COM IA --------- CONFIGURAÇÃO -------- FOTO COM IA ---------
# GEMINI
# Coloque aqui um modelo que esteja disponível para a sua API key.
GEMINI_MODEL = "gemini-3.6-flash"
# CONFIGURAÇÃO
CATEGORIAS = {
    "conteudo_sugestivo": "Conteúdo sugestivo",
    "lgbtismo": "LGBTismo",
    "satanismo_ocultismo": "Satanismo/ocultismo",
    "racismo": "Racismo",
    "violencia": "Violência",
    "drogas": "Drogas",
    "crimes": "Crimes",
}
# ANÁLISE DO GEMINI
async def analisar_foto_com_gemini(
    image_bytes: bytes,
    mime_type: str
):
    """
    Envia a imagem para o Gemini e retorna as pontuações.
    """

    prompt = """
Analise a imagem fornecida como foto de perfil de um membro de um servidor
Discord.

A imagem NÃO deve promover, fazer apologia ou incentivar nenhuma das
categorias abaixo:

1. Conteúdo sugestivo
2. LGBTismo
3. Satanismo/ocultismo
4. Racismo
5. Violência
6. Drogas
7. Crimes

Para CADA categoria, atribua uma pontuação inteira de 0 a 100.

IMPORTANTE:

- 0 significa que praticamente não há indício de violação daquela categoria.
- 100 significa que há evidência muito forte de que a imagem promove, faz
  apologia ou incentiva aquela categoria.
- A pontuação deve representar a força da evidência visual.
- Não dê pontuação alta simplesmente porque algo poderia ser interpretado de
  forma remota como relacionado à categoria.
- Contexto ambíguo deve receber uma pontuação menor.
- Não confunda simplesmente "representar" algo com "promover, fazer apologia
  ou incentivar" algo.
- Não invente elementos que não estão visíveis na imagem.
- Para racismo, considere símbolos, textos ou imagens claramente
  discriminatórios ou de supremacia racial.
- Para violência, não marque alto apenas porque existe uma arma ou uma cena
  fictícia; avalie se a imagem promove ou glorifica violência.
- Para crimes, avalie apologia, incentivo ou glorificação de atividades
  criminosas.
- Para drogas, avalie principalmente promoção, apologia ou incentivo.
- Para satanismo/ocultismo, avalie símbolos ou conteúdo claramente
  relacionado à promoção/apologia dessas práticas.
- Para conteúdo sugestivo, considere sexualização, nudez, poses ou imagens
  sexualmente explícitas/sugestivas.

Retorne SOMENTE o objeto JSON solicitado pelo schema.
"""

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type
    )

    # TENTAR ATÉ 3 VEZES
    for tentativa in range(3):

        api_key = proxima_api()
        client = genai.Client(api_key=api_key)

        try:
            
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    image_part,
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "conteudo_sugestivo": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "lgbtismo": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "satanismo_ocultismo": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "racismo": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "violencia": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "drogas": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "crimes": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            }
                        },
                        "required": [
                            "conteudo_sugestivo",
                            "lgbtismo",
                            "satanismo_ocultismo",
                            "racismo",
                            "violencia",
                            "drogas",
                            "crimes"
                        ]
                    }
                )
            )

            # SUCESSO
            return json.loads(response.text)

        except Exception as e:

            # Se for erro 429, coloca essa API em cooldown
            if "429" in str(e):
                marcar_api_como_indisponivel(api_key)
            
            # Ainda há tentativas
            if tentativa < 2:

                espera = 5 * (tentativa + 1)

                print(
                    f"[FOTOS] Gemini falhou "
                    f"(tentativa {tentativa + 1}/3): {e}"
                )

                await asyncio.sleep(espera)

            # Última tentativa também falhou
            else:

                print(
                    f"[FOTOS] Gemini falhou após "
                    f"3 tentativas: {e}"
                )

                raise
#endregion

# EVENTO DE ALTERAÇÃO DE MEMBRO -----------------------------------------------------------
@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # ---------------------------------- Ticket de entrada
    await asyncio.sleep(2)
    if before.pending and not after.pending:

        passou_direto = await membro_esta_na_thread_passar_direto(after)

        if passou_direto:
            await passar_membro_direto(after)
        else:
            await criar_ticket_entrada(after)

    # ------------------------------ cargo verificado e pedir_acesso
    # ---------------------------------- Alterações de cargos

    cargos_antes = {cargo.id for cargo in before.roles}
    cargos_depois = {cargo.id for cargo in after.roles}

    # Ganhou o cargo verificado
    if (
        cargo_verificado in cargos_depois
        and cargo_verificado not in cargos_antes
    ):
        mensagem = f"""<@{after.id}> se verificou.
-# <@&1419489233940512828>
        """

        await procurar_topico_e_enviar(
            after.guild,
            after,
            chat_convites,
            mensagem
        )

        await procurar_topico_e_enviar(
            after.guild,
            after,
            chat_ticket,
            mensagem
        )

    # Perdeu o cargo pedir acesso
    if (
        cargo_pedir_acesso in cargos_antes
        and cargo_pedir_acesso not in cargos_depois
    ):

        asyncio.create_task(
            criar_topico_privado_automatico(
            after.guild,
            after,
            obter_ou_criar_chat
        )
        )

        mensagem = f"<@{after.id}> acessou o servidor."

        await procurar_topico_e_enviar(
            after.guild,
            after,
            chat_convites,
            mensagem
        )

        await procurar_topico_e_enviar(
            after.guild,
            after,
            chat_ticket,
            mensagem
        )

    await verificar_destaque_do_dia(
        bot,
        before,
        after,
        cargo_destaque_do_dia,
        chat_thread_ddd_logs
    )
#endregion

#region on_user_update (análise de fotos com IA, mas o inicio tá em cima do on_member_update)
# EVENTO DE ALTERAÇÃO DE FOTO DE PERFIL
@bot.event
async def on_user_update(
    before: discord.User,
    after: discord.User
):
    # Ignora bots
    if after.bot:
        return
    # Verifica se o avatar realmente mudou
    if before.avatar == after.avatar:
        return
    # Se removeu a foto, não há imagem para analisar
    if after.avatar is None:
        return

    try:
        # PEGAR O SERVIDOR
        guild = bot.get_guild(1347727626088878151)

        if guild is None:
            print("[FOTOS] Servidor não encontrado.")
            return

        # PEGAR O MEMBRO
        membro = guild.get_member(after.id)

        if membro is None:
            print(
                f"[FOTOS] {after} não está no servidor."
            )
            return

        # BAIXAR AVATAR
        image_bytes = await after.avatar.read()

        # O Discord normalmente entrega PNG/JPEG/WebP.
        # A análise recebe os bytes diretamente.
        mime_type = "image/png"

        # ANALISAR COM IA
        resultado = await analisar_foto_com_gemini(
            image_bytes,
            mime_type
        )

        # LIMITAR OS VALORES POR SEGURANÇA
        pontuacoes = {}

        for chave in CATEGORIAS:
            valor = resultado.get(chave, 0)

            try:
                valor = int(valor)
            except (TypeError, ValueError):
                valor = 0

            valor = max(0, min(100, valor))
            pontuacoes[chave] = valor

        # VERIFICAR SE ALGUMA CATEGORIA PASSOU DE 60
        categorias_suspeitas = {
            chave: valor
            for chave, valor in pontuacoes.items()
            if valor > 60
        }

        precisa_moderador = (
            len(categorias_suspeitas) > 0
        )

        # PEGAR O CARGO DE MODERADOR
        role = guild.get_role(cargo_moderador)

        # PEGAR O CANAL/THREAD DE LOG
        canal_logs = guild.get_thread(
            chat_logs_thread_fotos
        )

        if canal_logs is None:
            print(
                f"[FOTOS] Não encontrei o canal/thread "
                f"{chat_logs_thread_fotos}"
            )
            return

        # CRIAR EMBED
        embed = discord.Embed(
            title="🖼️ Análise de foto de perfil",
            description=(
                f"**Membro:** {membro.mention}\n"
                f"**ID:** `{after.id}`"
            ),
            color=(
                discord.Color.red()
                if precisa_moderador
                else discord.Color.green()
            )
        )

        # ADICIONAR CADA PONTUAÇÃO
        for chave, nome in CATEGORIAS.items():

            valor = pontuacoes[chave]

            if valor > 60:
                indicador = "🔴"
            elif valor >= 40:
                indicador = "🟡"
            else:
                indicador = "🟢"

            embed.add_field(
                name=f"{indicador} {nome}",
                value=f"`{valor}/100`",
                inline=True
            )

        # STATUS
        if precisa_moderador:
            embed.add_field(
                name="⚠️ Status",
                value=(
                    "Uma ou mais categorias ultrapassaram "
                    "o limite de `60` e precisam de revisão."
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="✅ Status",
                value=(
                    "Nenhuma categoria ultrapassou `60`."
                ),
                inline=False
            )

        # COLOCAR A FOTO NO EMBED
        embed.set_image(
            url=after.display_avatar.url
        )

        # RODAPÉ
        embed.set_footer(
            text="Análise automática de foto de perfil"
        )

        # ENVIAR PARA OS MODERADORES SE NECESSÁRIO
        if precisa_moderador and role is not None:
            await canal_logs.send(
                content=role.mention,
                embed=embed
            )
        else:
            await canal_logs.send(
                embed=embed
            )

    except Exception as e:
        print(
            f"[FOTOS] Erro ao analisar avatar de "
            f"{after} ({after.id}): {e}"
        )
#endregion

#region --------------- Evento: SAIR do servidor
@bot.event
async def on_member_remove(member: discord.Member):
    for canal_id in (chat_convites, chat_ticket):
        canal = bot.get_channel(canal_id)

        if canal is None:
            continue

        # Tópicos ativos
        for thread in canal.threads:
            if str(member.id) in thread.name:
                await thread.send(f"⚠️ {member.mention} saiu do servidor.")
                break

        # Tópicos arquivados
        async for thread in canal.archived_threads(limit=None):
            if str(member.id) in thread.name:
                await thread.send(f"⚠️ {member.mention} saiu do servidor.")
                break
#endregion

#region -------------- /verificar_a_verificar
def formatar_tempo(td: timedelta):
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


def deve_ser_verificado(membro: discord.Member):
    cargos = {cargo.id for cargo in membro.roles}

    return (
        a_verificar in cargos or
        (
            cargo_conta_suspeita in cargos and
            cargo_pedir_acesso in cargos
        )
    )


class ViewExpulsar(discord.ui.View):
    def __init__(self, autor: discord.Member):
        super().__init__(timeout=10)
        self.autor = autor
        self.msg = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        if self.msg:
            await self.msg.edit(view=self)

    @discord.ui.button(
        label="Expulsar 3d+",
        style=discord.ButtonStyle.danger,
        emoji="🗑️"
    )
    async def expulsar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user != self.autor:
            await interaction.response.send_message(
                "Apenas quem executou o comando pode usar este botão.",
                ephemeral=True
            )
            return

        limite = datetime.now(timezone.utc) - timedelta(days=3)

        expulsos = 0

        for membro in interaction.guild.members:

            if not deve_ser_verificado(membro):
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
            view=self
        )


@bot.tree.command(
    name="verificar_a_verificar",
    description="Verifica membros com cargo de análise ou conta suspeita aguardando acesso."
)
async def verificar_a_verificar(interaction: discord.Interaction):

    if cargo_moderador not in [r.id for r in interaction.user.roles]:
        await interaction.response.send_message(
            "Você não possui permissão.",
            ephemeral=True
        )
        return

    membros = [
        m for m in interaction.guild.members
        if deve_ser_verificado(m)
    ]

    if not membros:
        await interaction.response.send_message(
            "Nenhum membro encontrado.",
            ephemeral=True
        )
        return

    agora = datetime.now(timezone.utc)

    linhas = []

    for membro in membros:

        tempo_servidor = agora - membro.joined_at
        idade_conta_ao_entrar = membro.joined_at - membro.created_at

        info = []

        if any(r.id == a_verificar for r in membro.roles):
            info.append("A verificar")

        if (
            any(r.id == cargo_conta_suspeita for r in membro.roles)
            and any(r.id == cargo_pedir_acesso for r in membro.roles)
        ):
            info.append("Conta suspeita + Pedir acesso")

        linhas.append(
            f"**{membro}** ({' | '.join(info)})\n"
            f"• Conta ao entrar: {formatar_tempo(idade_conta_ao_entrar)}\n"
            f"• No servidor: {formatar_tempo(tempo_servidor)}"
        )

    texto = "\n\n".join(linhas)

    if len(texto) > 1900:
        texto = texto[:1900] + "\n..."

    view = ViewExpulsar(interaction.user)

    await interaction.response.send_message(
        texto,
        view=view,
        ephemeral=True
    )

    view.msg = await interaction.original_response()
#endregion

#region -------------- Registrar Motivo de entrada
data_corte_de_procurar_convites = datetime(2026, 7, 1, tzinfo=timezone.utc)
@app_commands.context_menu(name="Motivo")
async def motivo(interaction: discord.Interaction, message: discord.Message):
    # Permissão
    if not any(r.id == cargo_recepcionista for r in interaction.user.roles):
        return await interaction.response.send_message(
            "Você não possui permissão.",
            ephemeral=True
        )

    try:
        await message.add_reaction("✅")
    except discord.Forbidden:
        pass  # O bot não tem permissão para adicionar reações
    except discord.HTTPException:
        pass  # Falha ao adicionar a reação

    membro = message.author

    await interaction.channel.send(
    f"{membro.mention}"
)

    # ---------------- Convite ----------------

    convite = "convite_vanity"

    canal_convites = bot.get_channel(chat_convites)

    if canal_convites is None:
        canal_convites = await bot.fetch_channel(chat_convites)

    async for msg in canal_convites.history(
    limit=None,
    after=data_corte_de_procurar_convites
):
        # Apenas mensagens do Invite Tracker Bot
        if msg.author.id != invite_tracker_bot:
            continue

        texto = msg.content

        # Verifica se é a mensagem desse membro
        if f"id: {membro.id}" not in texto.lower():
            continue

        encontrado = re.search(
            r"Convite:\s*([A-Za-z0-9_-]+)",
            texto,
            re.IGNORECASE
        )

        if encontrado:
            convite = encontrado.group(1)

        break

    # ---------------- Gênero ----------------

    if any(r.id == cargo_homem for r in membro.roles):
        genero = "Homem"

    elif any(r.id == cargo_mulher for r in membro.roles):
        genero = "Mulher"

    elif any(r.id == cargo_genero_nao_informado for r in membro.roles):
        genero = "Gênero não informado"

    else:
        genero = "Gênero não informado"

    # ---------------- Canal de logs ----------------

    canal_logs = bot.get_channel(chat_logs_thread_motivos)

    if canal_logs is None:
        canal_logs = await bot.fetch_channel(chat_logs_thread_motivos)

    texto_novo = message.content.strip()

    mensagem_existente = None

    async for msg in canal_logs.history(limit=None, oldest_first=True):

        if f"**ID:** {membro.id}" in msg.content:
            mensagem_existente = msg
            break

    if mensagem_existente:

        partes = mensagem_existente.content.split("**Mensagens:**", 1)

        mensagens = ""

        if len(partes) == 2:
            mensagens = partes[1].strip()

        if texto_novo not in mensagens:
            if mensagens:
                mensagens += "\n"
            mensagens += texto_novo

        await mensagem_existente.edit(
            content=(
                f"**ID:** {membro.id}\n"
                f"**Convite:** {convite}\n"
                f"**Gênero:** {genero}\n\n"
                f"**Mensagens:**\n"
                f"{mensagens}"
            )
        )

    else:

        await canal_logs.send(
            f"**ID:** {membro.id}\n"
            f"**Convite:** {convite}\n"
            f"**Gênero:** {genero}\n\n"
            f"**Mensagens:**\n"
            f"{texto_novo}"
        )

    await interaction.response.send_message(
        "Verifique o chat de logs.",
        ephemeral=True
    )

bot.tree.add_command(motivo)

#endregion

#region -------------- /remove role all

@bot.tree.command(
    name="remove_role_all",
    description="Remove um cargo de todos os membros."
)
@app_commands.describe(
    cargo="Cargo que será removido de todos."
)
async def remove_role_all(
    interaction: discord.Interaction,
    cargo: discord.Role
):

    # Permissão
    if not any(r.id == cargo_administrador for r in interaction.user.roles):
        return await interaction.response.send_message(
            "Você não possui permissão para usar este comando.",
            ephemeral=True
        )

    membros = [m for m in interaction.guild.members if cargo in m.roles]

    if not membros:
        return await interaction.response.send_message(
            "Ninguém possui esse cargo.",
            ephemeral=True
        )

    # Estimativa (0,4 s por membro)
    estimativa = len(membros) * 0.4

    minutos = int(estimativa // 60)
    segundos = int(estimativa % 60)

    if minutos:
        tempo_texto = f"{minutos} min {segundos} s"
    else:
        tempo_texto = f"{segundos} s"

    await interaction.response.send_message(
        f"Removendo **{cargo.name}** de **{len(membros)}** membros.\n"
        f"⏳ Tempo estimado: **{tempo_texto}**."
    )

    inicio = time.perf_counter()

    removidos = 0

    for membro in membros:
        try:
            await membro.remove_roles(
                cargo,
                reason=f"Remoção em massa por {interaction.user}"
            )
            removidos += 1
        except Exception:
            pass

        await asyncio.sleep(0.4)

    tempo_real = round(time.perf_counter() - inicio, 1)

    await interaction.followup.send(
        f"✅ Processo concluído!\n"
        f"Cargo removido de **{removidos}** membro(s).\n"
        f"⏱️ Tempo gasto: **{tempo_real} segundos**."
    )

#endregion

#region -------------- /limpar_dm
@bot.tree.command(
    name="limpar_dm",
    description="Apaga."
)
@app_commands.describe(membro="Selecione o usuário.")
async def limpar_dm(interaction: discord.Interaction, membro: discord.Member):

    # Verifica o cargo
    if cargo_moderador not in [cargo.id for cargo in interaction.user.roles]:
        await interaction.response.send_message(
            "❌ Você não possui permissão para usar este comando.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        dm = await membro.create_dm()

        apagadas = 0

        async for mensagem in dm.history(limit=None):
            if mensagem.author.id == bot.user.id:
                try:
                    await mensagem.delete()
                    apagadas += 1
                except discord.HTTPException:
                    pass

        await interaction.followup.send(
            f"✅ Apaguei {apagadas} mensagens da DM de {membro.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Não foi possível acessar a DM desse usuário.",
            ephemeral=True
        )

#endregion

#region -------------- /salvar_ids_cargo
@app_commands.command(
    name="salvar_ids_cargo",
    description="Salva os IDs de todos os membros de um cargo."
)
@app_commands.describe(cargo="Cargo cujos membros serão salvos")
async def salvar_ids_cargo(
    interaction: discord.Interaction,
    cargo: discord.Role
):
    # Verifica se possui o cargo de moderador
    if not any(role.id == cargo_administrador for role in interaction.user.roles):
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "💾 Estou salvando os IDs...",
        ephemeral=True
    )

    # Cria a pasta caso não exista
    os.makedirs("dados", exist_ok=True)

    # Nome do arquivo: NomeDoCargo_DD-MM-AAAA.json
    nome_cargo = re.sub(r'[<>:"/\\|?*]', '_', cargo.name).replace(" ", "_")
    data = datetime.now().strftime("%d-%m-%Y")
    caminho = f"dados/{nome_cargo}_{data}.json"

    # Salva os IDs
    ids = [membro.id for membro in cargo.members]

    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(ids, arquivo, indent=4)

    # Confirmação
    await interaction.followup.send(
        f"✅ Salvei todos os IDs do cargo **{cargo.name}** ({len(ids)} membros).",
        ephemeral=True
    )

    # Registro no chat de logs (sem mencionar o cargo)
    canal_logs = interaction.guild.get_channel(chat_logs)
    if canal_logs:
        await canal_logs.send(
            f"🗂️ {interaction.user.mention} salvou os IDs do cargo **{cargo.name}** "
            f"({len(ids)} membros)."
        )


bot.tree.add_command(salvar_ids_cargo)

#endregion

#region -------------- /transferir_cargos_em_massa
@bot.tree.command(
    name="transferir_cargo_em_massa",
    description="Remove um cargo e adiciona outro em todos os membros."
)
@app_commands.describe(
    cargo_base="Cargo que será removido",
    cargo_destino="Cargo que será adicionado",
    exceto_1="Quem possuir este cargo será ignorado",
    exceto_2="Quem possuir este cargo será ignorado",
    exceto_3="Quem possuir este cargo será ignorado",
    exceto_4="Quem possuir este cargo será ignorado"
)
async def transferir_cargo_em_massa(
    interaction: discord.Interaction,
    cargo_base: discord.Role,
    cargo_destino: discord.Role,
    exceto_1: discord.Role = None,
    exceto_2: discord.Role = None,
    exceto_3: discord.Role = None,
    exceto_4: discord.Role = None
):
    # Verifica permissão
    if cargo_administrador not in [cargo.id for cargo in interaction.user.roles]:
        return

    await interaction.response.defer(ephemeral=True)

    excecoes = {r for r in [exceto_1, exceto_2, exceto_3, exceto_4] if r is not None}

    transferidos = 0
    ignorados = 0
    erros = 0

    for membro in interaction.guild.members:

        # Precisa possuir o cargo base
        if cargo_base not in membro.roles:
            continue

        # Ignora quem possui algum cargo de exceção
        if any(cargo in membro.roles for cargo in excecoes):
            ignorados += 1
            continue

        try:
            await membro.remove_roles(
                cargo_base,
                reason=f"Transferência em massa realizada por {interaction.user}"
            )

            if cargo_destino not in membro.roles:
                await membro.add_roles(
                    cargo_destino,
                    reason=f"Transferência em massa realizada por {interaction.user}"
                )

            transferidos += 1

        except Exception:
            erros += 1

    # ===========================
    # Registro no chat de logs
    # ===========================
    canal_logs = interaction.guild.get_channel(chat_logs)

    if canal_logs:

        embed_logs = discord.Embed(
            title="📦 Transferência de cargos em massa",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        embed_logs.add_field(
            name="Executado por",
            value=f"{interaction.user} (`{interaction.user.id}`)",
            inline=False
        )

        embed_logs.add_field(
            name="Cargo base",
            value=f"`{cargo_base.name}`",
            inline=True
        )

        embed_logs.add_field(
            name="Cargo destino",
            value=f"`{cargo_destino.name}`",
            inline=True
        )

        excecoes_texto = "\n".join(
            f"`{cargo.name}`" for cargo in excecoes
        ) if excecoes else "Nenhuma"

        embed_logs.add_field(
            name="Cargos de exceção",
            value=excecoes_texto,
            inline=False
        )

        embed_logs.add_field(
            name="Resultado",
            value=(
                f"**Transferidos:** {transferidos}\n"
                f"**Ignorados:** {ignorados}\n"
                f"**Erros:** {erros}"
            ),
            inline=False
        )

        await canal_logs.send(embed=embed_logs)

    # ===========================
    # Resposta ao executor
    # ===========================
    embed = discord.Embed(
        title="Transferência concluída",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Transferidos",
        value=str(transferidos),
        inline=True
    )

    embed.add_field(
        name="Ignorados",
        value=str(ignorados),
        inline=True
    )

    embed.add_field(
        name="Erros",
        value=str(erros),
        inline=True
    )

    await interaction.followup.send(embed=embed, ephemeral=True)
#endregion

#region -------------- /adicionar_cargo_ativos
@bot.tree.command(
    name="adicionar_cargo_3d",
    description="Adiciona um cargo a quem enviou mensagem nos últimos 3 dias."
)
@app_commands.describe(
    cargo="Cargo que será adicionado"
)
async def adicionar_cargo_3d(
    interaction: discord.Interaction,
    cargo: discord.Role
):
    
    # Verifica permissão
    if cargo_administrador not in [cargo.id for cargo in interaction.user.roles]:
        return
    await interaction.response.defer(ephemeral=True)

    limite = datetime.now(timezone.utc) - timedelta(days=3)

    membros_ativos = set()

    # Percorre todos os canais de texto
    for canal in interaction.guild.text_channels:

        try:
            async for mensagem in canal.history(after=limite, limit=None):

                if mensagem.author.bot:
                    continue

                membro = interaction.guild.get_member(mensagem.author.id)

                if membro is None:
                    continue

                membros_ativos.add(membro)

            await asyncio.sleep(0.5)
            
        except (discord.Forbidden, discord.HTTPException, discord.DiscordServerError):
            continue

    adicionados = 0
    erros = 0

    for membro in membros_ativos:

        if cargo in membro.roles:
            continue

        try:
            await membro.add_roles(
                cargo,
                reason="Enviou mensagem nos últimos 3 dias."
            )
            adicionados += 1

        except Exception:
            erros += 1

    # Registro no chat de logs
    canal_logs = interaction.guild.get_channel(chat_logs)

    if canal_logs:
        embed = discord.Embed(
            title="📋 Cargo adicionado aos membros ativos",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="Executado por",
            value=f"{interaction.user} (`{interaction.user.id}`)",
            inline=False
        )

        embed.add_field(
            name="Cargo adicionado",
            value=f"`{cargo.name}`",
            inline=False
        )

        embed.add_field(
            name="Período analisado",
            value="Últimos **3 dias**",
            inline=False
        )

        embed.add_field(
            name="Resultado",
            value=(
                f"**Membros ativos encontrados:** {len(membros_ativos)}\n"
                f"**Cargo adicionado:** {adicionados}\n"
                f"**Erros:** {erros}"
            ),
            inline=False
        )

    await canal_logs.send(embed=embed)

    await interaction.followup.send(
        f"Concluído!\n\n"
        f"👥 Membros ativos encontrados: **{len(membros_ativos)}**\n"
        f"✅ Cargo adicionado: **{adicionados}**\n"
        f"❌ Erros: **{erros}**",
        ephemeral=True
    )
#endregion

#region -------------- /relembrar_pedir_acesso
@app_commands.command(
    name="relembrar_pedir_acesso",
    description="Lembra os membros de responderem ao pedido de acesso."
)
async def relembrar_pedir_acesso(interaction: discord.Interaction):

    # Permissão
    if cargo_administrador not in [c.id for c in interaction.user.roles]:
        return

    await interaction.response.send_message(
        "Iniciando envio dos lembretes...",
        ephemeral=True
    )

    guild = interaction.guild

    role = guild.get_role(cargo_pedir_acesso)
    forum = guild.get_channel(chat_ticket)
    logs = guild.get_channel(chat_logs)

    if role is None or forum is None or logs is None:
        return

    # Threads ativas
    threads = list(forum.threads)

    # Threads arquivadas
    async for thread in forum.archived_threads(limit=None):
        threads.append(thread)

    for membro in role.members:

        # Só aplica a membros que estão no servidor há mais de 36 horas
        if membro.joined_at is None:
            continue

        tempo_no_servidor = datetime.now(timezone.utc) - membro.joined_at

        if tempo_no_servidor.total_seconds() <= 36 * 60 * 60:
            continue

        thread_encontrada = None

        for thread in threads:
            if str(membro.id) in thread.name:
                thread_encontrada = thread
                break

        if thread_encontrada:

            dias = tempo_no_servidor.days

            await thread_encontrada.send(
                f"Olá, {membro.mention}!\n"
                f"Você está no servidor há **{dias} dias** e ainda não acessou o servidor. Leia as mensagens acima para darmos prosseguimento."
            )

            await logs.send(
                f"✅ Lembrete enviado para **{membro}** (`{membro.id}`) "
                f"no tópico {thread_encontrada.mention}."
            )

        else:

            await logs.send(
                f"⚠️ O membro **{membro}** (`{membro.id}`) não possui um tópico próprio em {forum.mention}."
            )

bot.tree.add_command(relembrar_pedir_acesso)
#endregion

#region -------------- criar convite
@bot.tree.command(name="criar_convite", description="Cria um convite permanente para um canal.")
@app_commands.describe(canal="Canal onde o convite será criado")
async def criar_convite(interaction: discord.Interaction, canal: discord.TextChannel):

    if cargo_administrador not in [cargo.id for cargo in interaction.user.roles]:
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
            ephemeral=True
        )
        return

    try:
        convite = await canal.create_invite(
            max_age=0,      # Nunca expira
            max_uses=0,     # Usos ilimitados
            unique=True,
            reason=f"Criado por {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Convite criado:\n{convite.url}",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Não tenho permissão para criar convites nesse canal.",
            ephemeral=True
        )
#endregion

#region Comando não encontrado
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    raise error
#endregion

#region Resumo com IA
# ------------------------------- RESUMIR COM GEMINI -----------------------------------
@bot.tree.command(
    name="resumir_com_gemini",
    description="Resume toda a conversa deste tópico usando IA."
)
async def resumir_com_gemini(interaction: discord.Interaction):

    # Verifica cargo
    cargo = discord.utils.get(interaction.user.roles, id=valentes)
    if cargo is None:
        await interaction.response.send_message(
            "Você não tem permissão para usar este comando.",
            ephemeral=True
        )
        return

    # Verifica se é thread
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message(
            "Este comando só pode ser usado dentro de um tópico.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    conversa = ""

    async for msg in interaction.channel.history(limit=None, oldest_first=True):
        if not msg.content.strip():
            continue

        conversa += f"{msg.author.display_name}: {msg.content}\n"

    if not conversa.strip():
        await interaction.followup.send("Não encontrei mensagens para resumir.")
        return

    try:

        #API rotativa
        client = genai.Client(api_key=proxima_api())

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"""
Você é um moderador imparcial.

Leia toda a conversa abaixo e produza um resumo claro e organizado.

Sua resposta deve conter:

# Tema
Explique qual era o assunto principal.

# Resumo
Resuma toda a discussão de forma objetiva.

# Principais argumentos
Liste os principais argumentos apresentados por cada lado.

# Conclusão
Explique como terminou, sem tomar partido.

Não invente informações. Baseie-se apenas na conversa.

{conversa}
"""
        )

        resumo = response.text
    
    

    except Exception as e:
        await interaction.followup.send(f"Erro ao gerar resumo:\n```{e}```")
        return

    # limite do Discord
    if len(resumo) <= 2000:
        await interaction.followup.send(f"## 📝 Resumo\n\n{resumo}")
    else:
        await interaction.followup.send("## 📝 Resumo")

        for i in range(0, len(resumo), 2000):
            await interaction.followup.send(resumo[i:i + 2000])

       
#endregion

#region Conversa no Privado--------------------------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # ANÁLISE AUTOMÁTICA DE IMAGENS -------------------------------
    await analisar_mensagem_de_imagem(
        bot,
        message
    )

    # PING STAFF ------------------------------------------------------------
    # Verifica se o cargo foi mencionado
    if any(role.id == ping_staff for role in message.role_mentions):

        cargo = message.guild.get_role(ping_staff)
        canal_logs = message.guild.get_channel(chat_logs)

        if cargo:
            link = message.jump_url

            texto = (
                f"🚨 **O cargo {cargo.name} foi marcado no servidor Bíblia em Foco.**\n\n"
                f"**Quem marcou:** {message.author.mention} ({message.author})\n"
                f"**Canal:** {message.channel.mention}\n\n"
                f"**Mensagem:**\n"
                f"{message.content}\n\n"
                f"**Ir para a mensagem:**\n{link}"
            )

            for membro in cargo.members:
                if membro.bot:
                    continue

                try:
                    await membro.send(texto)
                except (discord.Forbidden, discord.HTTPException):
                    pass

            if canal_logs:
                await canal_logs.send(texto)

    # MENSAGEM NA DM ----------------------------------------------------
    # Ignora mensagens do próprio bot
    if message.author.bot:
        return

    # Verifica se é uma mensagem privada
    if isinstance(message.channel, discord.DMChannel):

        canal_logs = bot.get_channel(chat_logs)

        if canal_logs:
            embed = discord.Embed(
                title="📩 Mensagem privada recebida",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.add_field(
                name="Usuário",
                value=f"{message.author.mention}\n`{message.author.id}`",
                inline=False
            )
            embed.add_field(
                name="Mensagem",
                value=message.content or "*Sem texto*",
                inline=False
            )
            if message.attachments:
                arquivos = "\n".join(anexo.url for anexo in message.attachments)
                embed.add_field(
                    name="Anexos",
                    value=arquivos,
                    inline=False
                )
            await canal_logs.send(embed=embed)
    # Mantém os comandos por prefixo funcionando
    await bot.process_commands(message)
#endregion

#region -------------- /cor
def converter_hex(codigo: str) -> discord.Colour | None:
    """
    Converte um código hexadecimal (#FFFFFF ou FFFFFF)
    para discord.Colour.
    """
    codigo = codigo.strip()

    if codigo.startswith("#"):
        codigo = codigo[1:]

    if not re.fullmatch(r"[0-9A-Fa-f]{6}", codigo):
        return None

    return discord.Colour(int(codigo, 16))


@bot.tree.command(name="cor", description="Define a cor do seu cargo de booster.")
@app_commands.describe(
    codigo="Código hexadecimal da cor principal. Ex: #FF0000",
    degradê="Código hexadecimal da segunda cor. Ex: #0000FF"
)
async def cor(
    interaction: discord.Interaction,
    codigo: str,
    degradê: str | None = None
):
    # CONFIGURAÇÕES

    guild = interaction.guild
    member = interaction.user

    # VERIFICAÇÕES BÁSICAS

    if guild is None or not isinstance(member, discord.Member):
        await interaction.response.send_message(
            "❌ Este comando só pode ser usado dentro de um servidor.",
            ephemeral=True
        )
        return

    # VERIFICAR CARGO BOOSTER
    role_booster = guild.get_role(cargo_booster)
    if role_booster is None:
        await interaction.response.send_message(
            "❌ O cargo de booster configurado no bot não foi encontrado.",
            ephemeral=True
        )
        return
    if role_booster not in member.roles:
        await interaction.response.send_message(
            "❌ Você precisa ter o cargo de booster para usar este comando.",
            ephemeral=True
        )
        return
    # VERIFICAR PERMISSÃO DO BOT
    bot_member = guild.me
    if bot_member is None:
        await interaction.response.send_message(
            "❌ Não consegui identificar o cargo do bot neste servidor.",
            ephemeral=True
        )
        return
    if not bot_member.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "❌ Eu preciso da permissão **Gerenciar Cargos** para fazer isso.",
            ephemeral=True
        )
        return

    # CONVERTER COR PRINCIPAL
    cor_principal = converter_hex(codigo)
    if cor_principal is None:
        await interaction.response.send_message(
            "❌ O código hexadecimal da cor principal é inválido.\n"
            "Use o formato `#FFFFFF` ou `FFFFFF`.",
            ephemeral=True
        )
        return
    # CONVERTER DEGRADÊ
    cor_secundaria = None
    if degradê is not None:

        cor_secundaria = converter_hex(degradê)

        if cor_secundaria is None:
            await interaction.response.send_message(
                "❌ O código hexadecimal do degradê é inválido.\n"
                "Use o formato `#FFFFFF` ou `FFFFFF`.",
                ephemeral=True
            )
            return
        # Verificar se o servidor possui Enhanced Role Styles
        if "ENHANCED_ROLE_STYLES" not in guild.features:
            await interaction.response.send_message(
                "❌ Este servidor não possui a opção de cargos com "
                "degradê ativada atualmente.",
                ephemeral=True
            )
            return

    nome_cargo = f"🎨 {member.name}"

    # Procurar cargo existente
    role = discord.utils.get(
        guild.roles,
        name=nome_cargo
    )

    # VERIFICAR SE O CARGO ENCONTRADO É GERENCIÁVEL
    if role is not None:

        if role.is_default():
            role = None

        elif role.managed:
            await interaction.response.send_message(
                "❌ Encontrei um cargo com esse nome, mas ele é "
                "gerenciado pelo Discord e não pode ser alterado.",
                ephemeral=True
            )
            return

        elif role >= bot_member.top_role:
            await interaction.response.send_message(
                "❌ O cargo de cor está acima ou no mesmo nível do "
                "meu cargo. Não consigo editá-lo.",
                ephemeral=True
            )
            return

    # CRIAR CARGO
    acao = None
    if role is None:

        try:

            role = await guild.create_role(
                name=nome_cargo,
                colour=cor_principal,
                secondary_colour=cor_secundaria,
                reason=f"Cargo de cor do booster {member} ({member.id})"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Não tenho permissão para criar cargos.",
                ephemeral=True
            )
            return

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ O Discord recusou a criação do cargo. "
                "Tente novamente.",
                ephemeral=True
            )
            return

        # POSICIONAR ABAIXO DO CARGO DO BOT
        try:

            await guild.edit_role_positions(
                positions={
                    role: bot_member.top_role.position - 1
                },
                reason=f"Posicionando cargo de cor de {member}"
            )

        except discord.Forbidden:
            # O cargo foi criado, mas não conseguimos posicioná-lo.
            # Não vamos apagar automaticamente.
            await interaction.response.send_message(
                "⚠️ O cargo foi criado, mas não consegui posicioná-lo "
                "abaixo do meu cargo. Verifique minha hierarquia.",
                ephemeral=True
            )

            return

        except discord.HTTPException:
            await interaction.response.send_message(
                "⚠️ O cargo foi criado, mas ocorreu um erro ao "
                "posicioná-lo.",
                ephemeral=True
            )

            return

        acao = "Cargo criado"

    # EDITAR CARGO EXISTENTE
    else:
        try:
            role = await role.edit(
                colour=cor_principal,
                secondary_colour=cor_secundaria,
                reason=f"Alteração de cor pelo booster {member} ({member.id})"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para editar esse cargo.",
                ephemeral=True
            )
            return

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ O Discord recusou a alteração do cargo.",
                ephemeral=True
            )
            return

        acao = "Cargo atualizado"

    # GARANTIR QUE O MEMBRO POSSUI O CARGO
    if role not in member.roles:
        try:
            await member.add_roles(
                role,
                reason=f"Cargo de cor do booster {member} ({member.id})"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "⚠️ A cor foi configurada, mas não consegui "
                "adicionar o cargo a você.",
                ephemeral=True
            )
            return

        except discord.HTTPException:

            await interaction.response.send_message(
                "⚠️ A cor foi configurada, mas ocorreu um erro "
                "ao adicionar o cargo.",
                ephemeral=True
            )
            return

    # RESPOSTA AO USUÁRIO
    if cor_secundaria is not None:
        mensagem = (
            f"🎨 Sua cor foi atualizada!\n\n"
            f"**Cor principal:** `{codigo.upper()}`\n"
            f"**Degradê:** `{degradê.upper()}`\n"
            f"**Cargo:** {role.mention}"
        )
        tipo_cor = "Degradê"

    else:
        mensagem = (
            f"🎨 Sua cor foi atualizada!\n\n"
            f"**Cor:** `{codigo.upper()}`\n"
            f"**Cargo:** {role.mention}"
        )
        tipo_cor = "Cor única"

    await interaction.response.send_message(
        mensagem,
        ephemeral=True
    )

    # LOG
    log_thread = guild.get_thread(chat_logs_thread_boosters)
    if log_thread is None:
        canal = guild.get_channel(chat_logs_thread_boosters)
        if isinstance(canal, discord.Thread):
            log_thread = canal

    if log_thread is not None:

        embed = discord.Embed(
            title="🎨 Alteração de cor de Booster",
            colour=cor_principal
        )

        embed.add_field(
            name="Usuário",
            value=f"{member.mention}\n`{member.name}`\n`{member.id}`",
            inline=False
        )

        embed.add_field(
            name="Cargo",
            value=f"{role.mention}\n`{role.name}`\n`{role.id}`",
            inline=False
        )

        embed.add_field(
            name="Tipo",
            value=tipo_cor,
            inline=True
        )

        embed.add_field(
            name="Cor principal",
            value=f"`{codigo.upper()}`",
            inline=True
        )

        embed.add_field(
            name="Degradê",
            value=f"`{degradê.upper()}`" if degradê else "Nenhum",
            inline=True
        )

        embed.add_field(
            name="Ação",
            value=acao,
            inline=False
        )

        embed.set_footer(
            text=f"ID do usuário: {member.id}"
        )

        try:
            await log_thread.send(embed=embed)

        except discord.Forbidden:
            pass

        except discord.HTTPException:
            pass
#endregion

#region -------------- /ranking_mdd
@bot.tree.command(name="ranking_mdd", description="Mostra o ranking de participação no chat de mensagem do dia.")
async def ranking(interaction: discord.Interaction):
    canal = interaction.guild.get_channel(chat_mensagem_do_dia)
    if canal is None:
        await interaction.response.send_message(
            "Não encontrei o canal de mensagens do dia.",
            ephemeral=True
        )
        return
    await interaction.response.defer()

    # Estruturas

    # Quantidade total de mensagens por usuário
    quantidade = defaultdict(int)

    # Dias em que cada usuário enviou pelo menos uma mensagem
    dias_usuario = defaultdict(set)

    # Primeira mensagem de cada usuário
    primeira_mensagem = {}

    # Guarda o nome/ID do usuário
    usuarios = {}

    # Quantidade de mensagens por dia
    mensagens_por_dia = defaultdict(int)

    # Percorrer TODO o histórico

    async for mensagem in canal.history(limit=None, oldest_first=True):

        # Ignora mensagens de bots
        if mensagem.author.bot:
            continue

        # Data no fuso local do Discord/Brasília.
        # Como o Discord fornece datetime com timezone, usamos apenas a data.
        dia = mensagem.created_at.date()

        usuario_id = mensagem.author.id

        quantidade[usuario_id] += 1
        dias_usuario[usuario_id].add(dia)
        mensagens_por_dia[dia] += 1

        usuarios[usuario_id] = mensagem.author

        # Como estamos usando oldest_first=True, a primeira ocorrência já é a primeira mensagem.
        if usuario_id not in primeira_mensagem:
            primeira_mensagem[usuario_id] = mensagem.created_at

    # Verificar se existe histórico
    if not mensagens_por_dia:
        await interaction.followup.send(
            "Não há mensagens no histórico desse canal."
        )
        return

    # Dias com atividade
    dias_com_mensagem = set(mensagens_por_dia.keys())

    # Número de dias em que alguém realmente mandou mensagem
    total_dias = len(dias_com_mensagem)

    # Montar ranking
    
    ranking_normal = []
    ranking_incompleto = []

    for usuario_id, total_mensagens in quantidade.items():

        autor = usuarios[usuario_id]

        # Detectar deleted_user
        
        # Se o Discord não conseguir resolver o usuário, normalmente o author ainda pode existir como objeto User. Portanto, aqui consideramos "deleted_user" quando o nome/username estiver exatamente assim. Se no seu servidor você usa outra identificação para usuários deletados, podemos adaptar.

        eh_deleted_user = (
            (getattr(autor, "name", "") or "").lower() == "deleted_user"
            or (getattr(autor, "global_name", "") or "").lower() == "deleted_user"
        )

        # Dias em que o usuário participou
        dias_participados = dias_usuario[usuario_id]

        # Participou de TODOS os dias que tiveram mensagens?
        participou_de_todos = (
            dias_participados == dias_com_mensagem
        )

        item = {
            "id": usuario_id,
            "usuario": autor,
            "quantidade": total_mensagens,
            "primeira_mensagem": primeira_mensagem[usuario_id],
            "dias": len(dias_participados),
            "deleted": eh_deleted_user
        }

        # Deleted_user sempre vai para baixo
        if eh_deleted_user:
            ranking_incompleto.append(item)

        # Quem faltou em algum dia também vai para baixo
        elif not participou_de_todos:
            ranking_incompleto.append(item)

        # Quem participou de todos os dias vai para cima
        else:
            ranking_normal.append(item)

    # Ordenação
    #
    # 1º - maior quantidade de mensagens
    # 2º - primeira mensagem mais antiga
    #

    ranking_normal.sort(
        key=lambda x: (
            -x["quantidade"],
            x["primeira_mensagem"]
        )
    )

    ranking_incompleto.sort(
        key=lambda x: (
            x["deleted"],       # deleted_user por último
            -x["quantidade"],
            x["primeira_mensagem"]
        )
    )

    ranking_final = ranking_normal + ranking_incompleto

    # Criar Embed

    embed = discord.Embed(
        title="🏆 Ranking de Mensagens do Dia",
        description=(
            f"Período analisado: **todo o histórico disponível**\n"
            f"Dias com atividade: **{total_dias}**"
        ),
        color=discord.Color.gold()
    )

    linhas = []

    for posicao, item in enumerate(ranking_final, start=1):

        usuario = item["usuario"]
        quantidade_msg = item["quantidade"]
        dias = item["dias"]

        # Medalhas
        if posicao == 1:
            prefixo = "🥇"
        elif posicao == 2:
            prefixo = "🥈"
        elif posicao == 3:
            prefixo = "🥉"
        else:
            prefixo = f"`{posicao}.`"

        # Indica quem não participou de todos os dias
        if item["deleted"]:
            status = " • `deleted_user`"

        elif dias < total_dias:
            status = f" • `{dias}/{total_dias} dias`"

        else:
            status = ""

        linhas.append(
            f"{prefixo} **{usuario.display_name}** — "
            f"**{quantidade_msg}** mensagens{status}"
        )

    # Discord limita embeds a 6000 caracteres. Vamos dividir caso fique muito grande.

    partes = []
    atual = ""

    for linha in linhas:

        if len(atual) + len(linha) + 1 > 4000:
            partes.append(atual)
            atual = ""

        atual += linha + "\n"

    if atual:
        partes.append(atual)

    # Primeiro embed
    embed.description += "\n\n" + partes[0]

    await interaction.followup.send(embed=embed)

    # Embeds adicionais
    for parte in partes[1:]:

        embed_extra = discord.Embed(
            description=parte,
            color=discord.Color.gold()
        )

        await interaction.followup.send(embed=embed_extra)
#endregion 

#region -------------- calls independentes e dependentes
# CALLS INDEPENDENTES -> CALLS DEPENDENTES
CALLS_DEPENDENTES = {
    eden: getsemani,
    sinai: oliveiras,
    jaco: laai_roi,
    salmos: canticos
}
# ATUALIZAR CALL DEPENDENTE

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

# EVENTO DE MUDANÇA DE CALL
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
#endregion

#region Marcar @ver_chat_explicação automaticamente
@tasks.loop(time=time(hour=20, minute=0, tzinfo=ZoneInfo("America/Sao_Paulo")))
async def lembrete_chat_explicacao():

    canal = bot.get_channel(chat_ticket_apolo)

    if canal is None:
        return

    mensagem = await canal.send(
        f"Crie um ticket <@&{cargo_ver_chat_explicacao}>"
    )

    await asyncio.sleep(10)

    try:
        await mensagem.delete()
    except discord.NotFound:
        pass
#endregion

#region --------------- /cor_destaque_do_dia
# ============================================================
# FUNÇÃO PARA CONVERTER HEX
# ============================================================

def converter_hex(valor: str):

    valor = valor.strip().replace("#", "")

    # Precisa ter exatamente 6 caracteres
    if len(valor) != 6:
        return None

    # Precisa ser hexadecimal
    try:
        numero = int(valor, 16)
    except ValueError:
        return None

    return discord.Color(numero)


# ============================================================
# MODAL DAS CORES
# ============================================================

class ModalCoresDestaque(discord.ui.Modal, title="Configurar cores"):

    primeira_cor = discord.ui.TextInput(
        label="Primeira cor",
        placeholder="#FF0000",
        required=True,
        max_length=7
    )

    segunda_cor = discord.ui.TextInput(
        label="Segunda cor",
        placeholder="#0000FF (opcional)",
        required=False,
        max_length=7
    )

    def __init__(self, cargo: discord.Role):
        super().__init__()

        self.cargo = cargo

    async def on_submit(self, interaction: discord.Interaction):

        # ----------------------------------------------------
        # PRIMEIRA COR
        # ----------------------------------------------------

        cor1 = converter_hex(self.primeira_cor.value)

        if cor1 is None:
            await interaction.response.send_message(
                "❌ A primeira cor não é um código hexadecimal válido.\n"
                "Use o formato `#RRGGBB`, por exemplo: `#FF0000`.",
                ephemeral=True
            )
            return

        # ----------------------------------------------------
        # SEGUNDA COR
        # ----------------------------------------------------

        valor_segunda = self.segunda_cor.value.strip()

        cor2 = None

        if valor_segunda:

            cor2 = converter_hex(valor_segunda)

            if cor2 is None:
                await interaction.response.send_message(
                    "❌ A segunda cor não é um código hexadecimal válido.\n"
                    "Use o formato `#RRGGBB`, por exemplo: `#0000FF`.",
                    ephemeral=True
                )
                return

        # ----------------------------------------------------
        # ALTERA A PRIMEIRA COR DO CARGO
        # ----------------------------------------------------

        try:

            await self.cargo.edit(
                color=cor1,
                reason=f"Cor do cargo alterada por {interaction.user}"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Não tenho permissão para alterar esse cargo.\n"
                "Verifique se o meu cargo está acima de "
                "`cargo_destaque_do_dia`.",
                ephemeral=True
            )
            return

        except discord.HTTPException as e:

            await interaction.response.send_message(
                f"❌ O Discord recusou a alteração do cargo.\n"
                f"Erro: `{e}`",
                ephemeral=True
            )
            return

        # ----------------------------------------------------
        # RESULTADO
        # ----------------------------------------------------

        if cor2:

            await interaction.response.send_message(
                f"✅ **Primeira cor salva:** `{self.primeira_cor.value}`\n"
                f"🎨 **Segunda cor salva:** `{self.segunda_cor.value}`\n\n"
                f"⚠️ A primeira cor do cargo foi alterada.\n"
                f"A segunda cor foi registrada, mas o degradê "
                f"deve ser aplicado pelo sistema do `/cor`.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                f"✅ **Cor salva com sucesso!**\n\n"
                f"🎨 Cor do cargo: `{self.primeira_cor.value}`\n"
                f"ℹ️ Nenhuma segunda cor foi informada.",
                ephemeral=True
            )


# ============================================================
# VIEW PRINCIPAL
# ============================================================

class ViewConfigurarDestaque(discord.ui.View):

    def __init__(self, cargo: discord.Role):
        super().__init__(timeout=None)

        self.cargo = cargo

    # --------------------------------------------------------
    # BOTÃO SALVAR
    # --------------------------------------------------------

    @discord.ui.button(
        label="Salvar",
        style=discord.ButtonStyle.success,
        emoji="💾",
        custom_id="destaque_salvar"
    )
    async def salvar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        # ----------------------------------------------------
        # PEGA OS CARGOS
        # ----------------------------------------------------

        cargo_destaque_role = interaction.guild.get_role(
            cargo_destaque_do_dia
        )

        cargo_adm_role = interaction.guild.get_role(
            cargo_administrador
        )

        # ----------------------------------------------------
        # VERIFICA PERMISSÃO
        # ----------------------------------------------------

        autorizado = (
            cargo_destaque_role in interaction.user.roles
            or
            cargo_adm_role in interaction.user.roles
        )

        if not autorizado:

            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este botão.",
                ephemeral=True
            )
            return

        # ----------------------------------------------------
        # ABRE O MODAL
        # ----------------------------------------------------

        await interaction.response.send_modal(
            ModalCoresDestaque(self.cargo)
        )


# ============================================================
# COMANDO
# ============================================================

@bot.tree.command(
    name="cor_destaque_do_dia",
    description="Configura as cores do cargo Destaque do Dia."
)
async def cor_destaque_do_dia(interaction: discord.Interaction):

    # --------------------------------------------------------
    # PEGA OS CARGOS
    # --------------------------------------------------------

    cargo_destaque_role = interaction.guild.get_role(
        cargo_destaque_do_dia
    )

    cargo_adm_role = interaction.guild.get_role(
        cargo_administrador
    )

    # --------------------------------------------------------
    # VERIFICA SE O CARGO EXISTE
    # --------------------------------------------------------

    if cargo_destaque_role is None:

        await interaction.response.send_message(
            "❌ Não encontrei o cargo `cargo_destaque_do_dia`.",
            ephemeral=True
        )
        return

    # --------------------------------------------------------
    # VERIFICA PERMISSÃO
    # --------------------------------------------------------

    autorizado = (
        cargo_destaque_role in interaction.user.roles
        or
        cargo_adm_role in interaction.user.roles
    )

    if not autorizado:

        await interaction.response.send_message(
            "❌ Você precisa possuir o cargo "
            "`cargo_destaque_do_dia` ou "
            "`cargo_administrador` para usar este comando.",
            ephemeral=True
        )
        return

    # --------------------------------------------------------
    # COR ATUAL
    # --------------------------------------------------------

    cor_atual = cargo_destaque_role.color

    hex_atual = f"#{cor_atual.value:06X}"

    # --------------------------------------------------------
    # EMBED 1
    # --------------------------------------------------------

    embed1 = discord.Embed(
        title="🎨 Primeira cor",
        description=(
            f"Cor atual do cargo:\n"
            f"`{hex_atual}`"
        ),
        color=cor_atual
    )

    # --------------------------------------------------------
    # EMBED 2
    # --------------------------------------------------------

    embed2 = discord.Embed(
        title="🎨 Segunda cor",
        description=(
            "Nenhuma segunda cor está configurada atualmente.\n\n"
            "Você poderá informar uma segunda cor ao clicar "
            "em **Salvar**."
        ),
        color=discord.Color.dark_grey()
    )

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    view = ViewConfigurarDestaque(
        cargo_destaque_role
    )

    # --------------------------------------------------------
    # ENVIA A MENSAGEM
    # --------------------------------------------------------

    await interaction.response.send_message(
        embeds=[
            embed1,
            embed2
        ],
        view=view
    )


#endregion

#region --------------- /alterar_apelido
@app_commands.command(
    name="alterar_apelido",
    description="Altera o apelido de outro membro."
)
@app_commands.describe(
    pessoa="Nome, apelido, menção ou ID da pessoa",
    novo_apelido="Novo apelido da pessoa"
)
async def alterar_apelido(
    interaction: discord.Interaction,
    pessoa: str,
    novo_apelido: str
):

    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ Este comando só pode ser usado dentro de um servidor.",
            ephemeral=True
        )
        return

    # ========================================================
    # VERIFICAR CARGOS
    # ========================================================

    possui_permissao = (
        cargo_destaque_do_dia in
        [cargo.id for cargo in interaction.user.roles]
        or
        cargo_booster in
        [cargo.id for cargo in interaction.user.roles]
    )

    if not possui_permissao:
        await interaction.response.send_message(
            "❌ Você precisa possuir o cargo "
            "`cargo_destaque_do_dia` ou `cargo_booster` "
            "para usar este comando.",
            ephemeral=True
        )
        return

    # ========================================================
    # PROCURAR A PESSOA
    # ========================================================

    pessoa = pessoa.strip()

    membro = None

    # --------------------------------------------------------
    # TENTAR PELO ID OU MENÇÃO
    # --------------------------------------------------------

    texto_id = (
        pessoa
        .replace("<@", "")
        .replace("!", "")
        .replace(">", "")
    )

    if texto_id.isdigit():

        membro = guild.get_member(
            int(texto_id)
        )

    # --------------------------------------------------------
    # TENTAR PELO NOME OU APELIDO
    # --------------------------------------------------------

    if membro is None:

        pessoa_lower = pessoa.lower()

        membro = discord.utils.find(
            lambda m: (
                m.name.lower() == pessoa_lower
                or
                m.display_name.lower() == pessoa_lower
            ),
            guild.members
        )

    # ========================================================
    # PESSOA NÃO ENCONTRADA
    # ========================================================

    if membro is None:

        await interaction.response.send_message(
            "❌ Não encontrei essa pessoa no servidor.\n\n"
            "Você pode informar o nome, apelido, @menção ou ID.",
            ephemeral=True
        )
        return

    # ========================================================
    # VERIFICAR NOVO APELIDO
    # ========================================================

    novo_apelido = novo_apelido.strip()

    if not novo_apelido:

        await interaction.response.send_message(
            "❌ O novo apelido não pode estar vazio.",
            ephemeral=True
        )
        return

    if len(novo_apelido) > 32:

        await interaction.response.send_message(
            "❌ O novo apelido pode ter no máximo 32 caracteres.",
            ephemeral=True
        )
        return

    # ========================================================
    # BUSCAR A THREAD DE LOGS
    # ========================================================

    thread_logs = guild.get_thread(
        chat_logs_threads_apelidos_DDD
    )

    # Caso a thread não esteja no cache, tentar buscar pela API
    if thread_logs is None:

        try:

            thread_logs = await guild.fetch_channel(
                chat_logs_threads_apelidos_DDD
            )

        except discord.NotFound:

            await interaction.response.send_message(
                "❌ Não encontrei a thread de logs de apelidos.",
                ephemeral=True
            )
            return

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Não tenho permissão para acessar "
                "a thread de logs de apelidos.",
                ephemeral=True
            )
            return

        except discord.HTTPException as e:

            print(
                f"[APELIDOS] Erro ao buscar thread de logs: {e}"
            )

            await interaction.response.send_message(
                "❌ Ocorreu um erro ao acessar a thread de logs.",
                ephemeral=True
            )
            return

    # Garantir que realmente é uma thread
    if not isinstance(thread_logs, discord.Thread):

        await interaction.response.send_message(
            "❌ O ID configurado em "
            "`chat_logs_threads_apelidos_DDD` "
            "não corresponde a uma thread.",
            ephemeral=True
        )
        return

    # ========================================================
    # DATA ATUAL - HORÁRIO DE BRASÍLIA
    # ========================================================

    agora = datetime.now(
        ZoneInfo("America/Sao_Paulo")
    )

    data_atual = agora.strftime(
        "%Y-%m-%d"
    )

    # ========================================================
    # CONTAR ALTERAÇÕES FEITAS HOJE
    # ========================================================

    quantidade_alteracoes = 0

    try:

        async for mensagem in thread_logs.history(
            limit=None
        ):

            texto = mensagem.content

            # Só considerar mensagens de hoje
            if not texto.startswith(data_atual):
                continue

            # Procurar o ID de quem executou
            if (
                f"Executor: {interaction.user.id}"
                not in texto
            ):
                continue

            quantidade_alteracoes += 1

            if quantidade_alteracoes >= 3:
                break

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Não tenho permissão para ler "
            "o histórico da thread de logs.",
            ephemeral=True
        )
        return

    except Exception as e:

        print(
            f"[APELIDOS] Erro ao verificar histórico: {e}"
        )

        await interaction.response.send_message(
            "❌ Ocorreu um erro ao verificar "
            "seu limite diário.",
            ephemeral=True
        )
        return

    # ========================================================
    # VERIFICAR LIMITE
    # ========================================================

    if quantidade_alteracoes >= 3:

        await interaction.response.send_message(
            "❌ Você já atingiu o limite de "
            "**3 alterações de apelido hoje**.",
            ephemeral=True
        )
        return

    # ========================================================
    # VERIFICAR HIERARQUIA DO BOT
    # ========================================================

    bot_member = guild.me

    if bot_member is None:

        await interaction.response.send_message(
            "❌ Não consegui identificar o bot no servidor.",
            ephemeral=True
        )
        return

    # Dono do servidor
    if membro == guild.owner:

        await interaction.response.send_message(
            "❌ Não é possível alterar o apelido "
            "do dono do servidor.",
            ephemeral=True
        )
        return

    # Próprio bot
    if membro == bot_member:

        await interaction.response.send_message(
            "❌ Não posso alterar meu próprio apelido "
            "através deste comando.",
            ephemeral=True
        )
        return

    # Hierarquia
    if membro.top_role >= bot_member.top_role:

        await interaction.response.send_message(
            "❌ Não posso alterar o apelido dessa pessoa "
            "porque o cargo mais alto dela é igual ou "
            "superior ao meu.",
            ephemeral=True
        )
        return

    # ========================================================
    # APELIDO ANTIGO
    # ========================================================

    apelido_antigo = membro.display_name

    # ========================================================
    # ALTERAR APELIDO
    # ========================================================

    try:

        await membro.edit(
            nick=novo_apelido,
            reason=(
                f"Alteração de apelido por "
                f"{interaction.user} "
                f"({interaction.user.id})"
            )
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ O Discord não permitiu alterar "
            "o apelido dessa pessoa.",
            ephemeral=True
        )
        return

    except discord.HTTPException as e:

        print(
            f"[APELIDOS] Erro ao alterar apelido: {e}"
        )

        await interaction.response.send_message(
            "❌ Ocorreu um erro ao alterar o apelido.",
            ephemeral=True
        )
        return

    # ========================================================
    # NÚMERO DA ALTERAÇÃO
    # ========================================================

    numero_alteracao = quantidade_alteracoes + 1

    # ========================================================
    # REGISTRAR NA THREAD
    # ========================================================

    mensagem_log = (
        f"{data_atual} | "
        f"Executor: {interaction.user.id} | "
        f"Alvo: {membro.id} | "
        f"Antigo: {apelido_antigo} | "
        f"Novo: {novo_apelido} | "
        f"Alteração: {numero_alteracao}/3"
    )

    try:

        await thread_logs.send(
            mensagem_log
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            f"✅ O apelido de {membro.mention} "
            f"foi alterado para **{novo_apelido}**.\n\n"
            "⚠️ Porém, não consegui registrar "
            "a alteração na thread de logs.",
            ephemeral=True
        )
        return

    except discord.HTTPException as e:

        print(
            f"[APELIDOS] Erro ao registrar log: {e}"
        )

    # ========================================================
    # CONFIRMAÇÃO
    # ========================================================

    await interaction.response.send_message(
        f"✅ **Apelido alterado com sucesso!**\n\n"
        f"👤 **Pessoa:** {membro.mention}\n"
        f"📝 **Apelido anterior:** {apelido_antigo}\n"
        f"✏️ **Novo apelido:** {novo_apelido}\n"
        f"📊 **Alterações hoje:** "
        f"{numero_alteracao}/3",
        ephemeral=True
    )


# ============================================================
# ADICIONAR O COMANDO À ÁRVORE
# ============================================================

bot.tree.add_command(
    alterar_apelido
)

#endregion

bot.run(TOKEN)