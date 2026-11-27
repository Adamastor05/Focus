"""
AGENDAR: ANALISAR_PFP

Reanalisa uma foto de perfil que ficou no logs de espera (Gemini e Groq falharam).

Formato (o bot escreve essa mensagem sozinho em CHAT_AGENDAMENTOS quando manda uma foto
para a espera; o gerenciador troca "+10 min" pela data e hora):

    AGENDAR: ANALISAR_PFP
    QUANDO: +10 min
    Motivo: Reanalisar foto de perfil de <@id> (Gemini e Groq falharam)
    Se_passar: Prosseguir
    Link: https://discord.com/channels/<servidor>/<thread de espera>/<mensagem>

O único dado necessário é o Link da mensagem que está no logs de espera: dela saem a imagem
(anexo), a pessoa (ID na embed) e a origem. Se a mensagem não tiver imagem (o download
da foto tinha falhado), usa a foto atual da pessoa.

Na hora:
  - analisa (Gemini -> Groq), registra no log, abre o tópico se passar de 60 e APAGA a
    mensagem do logs de espera;
  - se Gemini e Groq falharem de novo, a mensagem fica na espera e um novo agendamento
    é criado para daqui a 10 minutos.
"""
from __future__ import annotations

import re

import discord

from config.IDs import BIBLIA_EM_FOCO, CHAT_AGENDAMENTOS, CHAT_THREAD_LOGS_EM_ESPERA
from comandos.slash.analisar_foto_perfil import (
    FalhaNasDuasIAs,
    baixar_avatar,
    descrever_erro,
    obter_canal,
)
from sistemas.analise_pfp.analisar_foto_perfil import (
    analisar_imagem_de_perfil,
    origem_pelo_texto,
)
from sistemas.analise_pfp.perfil_suspeito import buscar_caso_aberto

ATRASO_REAGENDAR = "+10 min"

_LINK_RE = re.compile(r"https?://(?:\w+\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)")
_ID_RE = re.compile(r"ID:\*\*\s*`(\d{15,20})`")


class _LinkInvalido(Exception):
    """Link ausente/errado ou mensagem que não é uma foto em espera do bot."""


class _MensagemNaoExiste(Exception):
    """A mensagem do logs de espera não existe mais."""


# ---------------------------------------------------------------- criar o agendamento
def _texto_agendamento(link: str, membro_id: int) -> str:
    return (
        "AGENDAR: ANALISAR_PFP\n"
        f"QUANDO: {ATRASO_REAGENDAR}\n"
        f"Motivo: Reanalisar foto de perfil de <@{membro_id}> (Gemini e Groq falharam)\n"
        "Se_passar: Prosseguir\n"
        f"Link: {link}"
    )


async def solicitar_agendamento(bot, link: str, membro_id: int) -> None:
    """Envia em CHAT_AGENDAMENTOS a mensagem que agenda a reanálise (daqui a 10 min)."""
    canal = await obter_canal(bot, int(CHAT_AGENDAMENTOS))
    if isinstance(canal, discord.Thread) and canal.archived:
        await canal.edit(archived=False)
    await canal.send(
        _texto_agendamento(link, membro_id),
        allowed_mentions=discord.AllowedMentions.none(),
        suppress_embeds=True,
    )


# ---------------------------------------------------------------- leitura do link
async def _carregar(bot, dados: dict) -> tuple[discord.Message, int]:
    """Retorna (mensagem do logs de espera, id da pessoa)."""
    link = dados["campos"].get("LINK", "")
    m = _LINK_RE.search(link)
    if not m:
        raise _LinkInvalido(
            "Falta o campo `Link` com o link da mensagem do logs de espera "
            "(`https://discord.com/channels/...`)."
        )
    _, canal_id, msg_id = (int(x) for x in m.groups())

    # A thread de espera pode ficar em outro servidor que o do chat de agendamentos,
    # então a trava é o id da thread (e não o servidor do link).
    if canal_id != int(CHAT_THREAD_LOGS_EM_ESPERA):
        raise _LinkInvalido("O link precisa ser de uma mensagem da thread de logs de espera.")

    canal = await obter_canal(bot, canal_id)
    try:
        msg = await canal.fetch_message(msg_id)
    except discord.NotFound:
        raise _MensagemNaoExiste("A mensagem do link não existe mais no logs de espera.")

    if msg.author.id != bot.user.id or not msg.embeds:
        raise _LinkInvalido("Essa mensagem não é uma foto em espera enviada pelo bot.")
    achado = _ID_RE.search(msg.embeds[0].description or "")
    if not achado:
        raise _LinkInvalido("Não encontrei o ID da pessoa nessa mensagem.")
    return msg, int(achado.group(1))


async def _obter_imagem(msg: discord.Message, membro: discord.Member) -> bytes:
    """Anexo da mensagem de espera; se não houver (ou falhar), a foto atual da pessoa."""
    if msg.attachments:
        try:
            return await msg.attachments[0].read()
        except discord.HTTPException:
            pass
    return await baixar_avatar(membro)


# ---------------------------------------------------------------- ação
async def executar(bot, dados: dict, validar: bool = False):
    try:
        msg, membro_id = await _carregar(bot, dados)
    except (_LinkInvalido, _MensagemNaoExiste) as e:
        if validar:
            return str(e)
        if isinstance(e, _MensagemNaoExiste):
            return "A mensagem já não está no logs de espera; nada a analisar."
        raise ValueError(str(e))

    if validar:
        return None

    guild = bot.get_guild(int(BIBLIA_EM_FOCO))  # servidor das fotos (não o do chat de agendamentos)
    if guild is None:
        raise RuntimeError("Servidor principal (BIBLIA_EM_FOCO) não encontrado pelo bot.")
    membro = guild.get_member(membro_id)
    if membro is None:
        try:
            membro = await guild.fetch_member(membro_id)
        except discord.NotFound:
            await _apagar_espera(msg)
            return "A pessoa não está mais no servidor: foto removida do logs de espera sem análise."

    origem = origem_pelo_texto(msg.embeds[0].description or "")

    motivo_falha = None
    imagem = None
    try:
        imagem = await _obter_imagem(msg, membro)
    except Exception as e:
        motivo_falha = f"não consegui obter a imagem: {descrever_erro(e)}"

    if imagem is not None:
        try:
            await analisar_imagem_de_perfil(
                bot, membro, origem, imagem, buscar_caso_aberto(bot, membro.id)
            )
        except FalhaNasDuasIAs as e:
            motivo_falha = f"Gemini: {e.motivo_gemini} | Groq: {e.motivo_groq}"

    if motivo_falha is None:
        apagou = await _apagar_espera(msg)
        return "Foto analisada" + (
            " e removida do logs de espera." if apagou else ". Não consegui apagá-la do logs de espera."
        )

    # Falhou de novo: a mensagem fica na espera e agenda mais uma tentativa.
    await solicitar_agendamento(bot, msg.jump_url, membro_id)
    return f"Falhou de novo ({motivo_falha[:600]}). Reagendado para daqui a 10 min."


async def _apagar_espera(msg: discord.Message) -> bool:
    try:
        await msg.delete()
        return True
    except discord.NotFound:
        return True
    except discord.HTTPException as e:
        print(f"[PERFIL] Não consegui apagar a mensagem de espera {msg.id}: {e}")
        return False