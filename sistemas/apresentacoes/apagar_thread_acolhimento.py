# Esse código serve para:
# 1- Detectar quando alguém cria uma thread no fórum de apresentações
# 2- Verificar se a pessoa tem o cargo de novato (se não tiver, não faz nada)
# 3- Procurar no chat de agendamentos o agendamento "Apagar thread do ping de acolhimento de {ID}"
# 4- Atualizar o campo "QUANDO" desse agendamento para o horário atual
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import discord

from config.IDs import (
    CHAT_FORUM_APRESENTACOES,
    CARGO_NOVATOS,
    CHAT_AGENDAMENTOS,
)

# Fuso horário usado no "QUANDO" (ajuste se necessário)
FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")
FORMATO_DATA = "%d/%m/%Y %H:%M"

# Quantas mensagens recentes do chat de agendamentos serão varridas
LIMITE_HISTORICO = 300

# "QUANDO: 21/11/2026 21:55" (qualquer caixa; aceita **negrito** e espaços)
REGEX_QUANDO = re.compile(
    r"(quando\s*\**\s*:\s*\**\s*)(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2})",
    re.IGNORECASE,
)
# Data solta, usada quando o "Quando" é o nome de um field de embed
REGEX_DATA = re.compile(r"\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}")


def _regex_motivo(user_id: int) -> re.Pattern:
    # Aceita o ID puro ou como menção (<@id>, <@!id>)
    return re.compile(
        rf"motivo\s*\**\s*:\s*\**\s*apagar thread do ping de acolhimento de\s*<?@?!?{user_id}>?",
        re.IGNORECASE,
    )


def _textos_da_mensagem(msg: discord.Message) -> str:
    """Junta conteúdo + embeds em um único texto para procurar o motivo."""
    partes = [msg.content or ""]
    for e in msg.embeds:
        partes += [e.title or "", e.description or ""]
        for f in e.fields:
            partes += [f.name or "", f.value or ""]
    return "\n".join(partes)


def _atualizar_mensagem(msg: discord.Message, agora: str) -> dict | None:
    """
    Devolve os kwargs para msg.edit() com o QUANDO atualizado,
    ou None se não encontrou nenhum campo QUANDO para editar.
    """
    kwargs = {}

    # 1) Mensagem de texto comum
    if msg.content:
        novo, n = REGEX_QUANDO.subn(lambda m: m.group(1) + agora, msg.content)
        if n:
            kwargs["content"] = novo

    # 2) Embeds
    if msg.embeds:
        embeds_novos = []
        embed_alterado = False

        for original in msg.embeds:
            embed = discord.Embed.from_dict(original.to_dict())

            if embed.description:
                novo, n = REGEX_QUANDO.subn(lambda m: m.group(1) + agora, embed.description)
                if n:
                    embed.description = novo
                    embed_alterado = True

            for i, f in enumerate(embed.fields):
                novo_valor = f.value
                alterou = False

                # Field com nome "Quando" e valor só com a data
                if f.name and f.name.strip(" :*").lower() == "quando":
                    novo_valor, n = REGEX_DATA.subn(agora, f.value, count=1)
                    alterou = n > 0
                # Ou "QUANDO: data" dentro do valor
                else:
                    novo_valor, n = REGEX_QUANDO.subn(lambda m: m.group(1) + agora, f.value)
                    alterou = n > 0

                if alterou:
                    embed.set_field_at(i, name=f.name, value=novo_valor, inline=f.inline)
                    embed_alterado = True

            embeds_novos.append(embed)

        if embed_alterado:
            kwargs["embeds"] = embeds_novos

    return kwargs or None


def registrar_evento_atualizar_agendamento(bot):

    @bot.listen("on_thread_create")
    async def atualizar_agendamento_thread_create(thread: discord.Thread):
        # Só nos interessa o fórum de apresentações
        if thread.parent_id != CHAT_FORUM_APRESENTACOES:
            return

        guild = thread.guild

        #region Autor
        autor = thread.owner or guild.get_member(thread.owner_id)

        if autor is None and thread.owner_id:
            try:
                autor = await guild.fetch_member(thread.owner_id)
            except discord.HTTPException:
                return

        if autor is None:
            return
        #endregion

        #region Verificar cargo de novato
        if autor.get_role(CARGO_NOVATOS) is None:
            return
        #endregion

        #region Procurar o agendamento
        canal = bot.get_channel(CHAT_AGENDAMENTOS)
        if canal is None:
            try:
                canal = await bot.fetch_channel(CHAT_AGENDAMENTOS)
            except discord.HTTPException:
                print("[atualizar_agendamento] Chat de agendamentos não encontrado.")
                return

        padrao_motivo = _regex_motivo(autor.id)
        alvo = None

        try:
            async for msg in canal.history(limit=LIMITE_HISTORICO):
                if padrao_motivo.search(_textos_da_mensagem(msg)):
                    alvo = msg
                    break
        except discord.HTTPException as e:
            print(f"[atualizar_agendamento] Erro ao ler o histórico: {e}")
            return

        if alvo is None:
            print(f"[atualizar_agendamento] Nenhum agendamento encontrado para {autor.id}.")
            return
        #endregion

        #region Editar o QUANDO
        agora = datetime.now(FUSO_HORARIO).strftime(FORMATO_DATA)
        edicao = _atualizar_mensagem(alvo, agora)

        if edicao is None:
            print(f"[atualizar_agendamento] Campo QUANDO não encontrado na mensagem {alvo.id}.")
            return

        try:
            await alvo.edit(**edicao)
        except discord.Forbidden:
            print(
                f"[atualizar_agendamento] Sem permissão para editar a mensagem {alvo.id} "
                "(só é possível editar mensagens enviadas pelo próprio bot)."
            )
        except discord.HTTPException as e:
            print(f"[atualizar_agendamento] Falha ao editar a mensagem {alvo.id}: {e}")
        #endregion