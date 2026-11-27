"""Análise da foto de perfil: Gemini -> Groq -> thread de espera.

Aqui fica a função em si (sem nenhum listener). Quem chama é o perfil_listeners.py.
Se alguma categoria passar de LIMITE_PONTOS, a segunda parte (perfil_suspeito.py) entra em ação.
"""
import asyncio
import io
import json
import re

import discord
from google.genai import errors as genai_errors
from google.genai import types

from config.IDs import CHAT_THREAD_LOGS_ANALISE_DE_PERFIL, CHAT_THREAD_LOGS_EM_ESPERA
from gemini_manager import proxima_api, marcar_api_como_indisponivel, quantidade_apis
from groq_manager import analisar_imagem as groq_analisar_imagem
from comandos.slash.analisar_foto_perfil import (
    GEMINI_MODELO,
    CODIGOS_TENTAR_OUTRA_API,
    Gemini503,
    GeminiSemApis,
    FalhaNasDuasIAs,
    _client,
    baixar_avatar,
    descrever_erro,
    log,
    obter_canal,
)
from sistemas.analise_pfp.perfil_denuncia import DenunciarView
from sistemas.analise_pfp.perfil_suspeito import (
    abrir_caso,
    avisar_nova_foto_suspeita,
    avisar_troca_de_foto,
    buscar_caso_aberto,
)

# ======================= CONFIG =======================
LIMITE_PONTOS = 60  # acima disso vai para a segunda parte (perfil_suspeito.py)

CATEGORIAS = {
    "conteudo_sugestivo": "Conteúdo sugestivo",
    "lgbtismo": "LGBTismo",
    "satanismo_ocultismo": "Satanismo/ocultismo",
    "racismo": "Racismo",
    "violencia": "Violência",
    "drogas": "Drogas",
    "crimes": "Crimes",
}

ORIGENS = {
    "entrada": "Entrou no servidor",
    "troca": "Trocou a foto de perfil",
    "espera": "Reanálise (estava em espera)",
}


def origem_pelo_texto(texto: str) -> str:
    """Descobre a origem ("entrada"/"troca") a partir do texto da embed de espera."""
    for chave, rotulo in ORIGENS.items():
        if rotulo in texto:
            return chave
    return "espera"

# No máximo 3 análises ao mesmo tempo (evita estourar as APIs quando entra muita gente).
_semaforo = asyncio.Semaphore(3)

PROMPT = """
Analise a imagem fornecida como foto de perfil de um membro de um servidor Discord.

A imagem NÃO deve promover, fazer apologia ou incentivar nenhuma das categorias abaixo:

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
- 100 significa que há evidência muito forte de que a imagem promove, faz apologia ou incentiva aquela categoria.
- A pontuação deve representar a força da evidência visual.
- Não dê pontuação alta simplesmente porque algo poderia ser interpretado de forma remota como relacionado à categoria.
- Contexto ambíguo deve receber uma pontuação menor.
- Não confunda simplesmente "representar" algo com "promover, fazer apologia ou incentivar" algo.
- Não invente elementos que não estão visíveis na imagem.
- Para conteúdo sugestivo, considere também homens e mulheres sem camisa.
- Para racismo, considere símbolos, textos ou imagens claramente discriminatórios ou de supremacia racial.
- Para violência, não marque alto apenas porque existe uma arma ou uma cena fictícia; avalie se a imagem promove ou glorifica violência.
- Para crimes, avalie apologia, incentivo ou glorificação de atividades criminosas.
- Para drogas, avalie principalmente promoção, apologia ou incentivo.
- Para satanismo/ocultismo, avalie símbolos ou conteúdo claramente relacionado à promoção/apologia dessas práticas.
- Para conteúdo sugestivo, considere sexualização, nudez, poses ou imagens sexualmente explícitas/sugestivas.
"""

PROMPT_GEMINI = PROMPT + "\nRetorne SOMENTE o objeto JSON solicitado pelo schema."

# A Groq força response_format=json_object, então o prompt precisa pedir o JSON e as chaves.
PROMPT_GROQ = (
    PROMPT
    + "\nResponda SOMENTE com um objeto JSON válido, sem nenhum texto fora do JSON, "
    "com exatamente estas chaves e valores inteiros de 0 a 100:\n"
    + json.dumps({k: 0 for k in CATEGORIAS})
)

SCHEMA = {
    "type": "object",
    "properties": {
        k: {"type": "integer", "minimum": 0, "maximum": 100} for k in CATEGORIAS
    },
    "required": list(CATEGORIAS),
}


# ======================= VALIDAÇÃO =======================
def _normalizar(dados) -> dict[str, int]:
    """Garante as 7 categorias como inteiros de 0 a 100; senão levanta ValueError."""
    if not isinstance(dados, dict):
        raise ValueError("A resposta da IA não é um objeto JSON.")

    pontuacoes = {}
    for chave in CATEGORIAS:
        if chave not in dados:
            raise ValueError(f"A resposta da IA não trouxe a categoria '{chave}'.")
        try:
            valor = int(round(float(dados[chave])))
        except (TypeError, ValueError):
            raise ValueError(f"Valor inválido para '{chave}': {dados[chave]!r}")
        pontuacoes[chave] = max(0, min(100, valor))
    return pontuacoes


# ======================= GEMINI =======================
async def classificar_com_gemini(imagem: bytes) -> tuple[dict[str, int], int]:
    """
    - 429/409: coloca a API em cooldown e tenta a próxima.
    - 503: levanta Gemini503 (não adianta tentar outras APIs).
    - Sem APIs disponíveis: levanta GeminiSemApis.
    Retorna (pontuacoes, quantidade_de_apis_tentadas).
    """
    contents = [
        types.Part.from_bytes(data=imagem, mime_type="image/png"),
        PROMPT_GEMINI,
    ]
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=SCHEMA,
    )

    tentativas = 0
    for _ in range(max(quantidade_apis(), 1)):
        try:
            api_key = proxima_api()
        except RuntimeError as e:
            raise GeminiSemApis(str(e)) from e

        tentativas += 1
        try:
            resp = await _client(api_key).aio.models.generate_content(
                model=GEMINI_MODELO, contents=contents, config=config
            )
        except genai_errors.APIError as e:
            if e.code in CODIGOS_TENTAR_OUTRA_API:
                marcar_api_como_indisponivel(api_key)
                continue
            if e.code == 503:
                raise Gemini503(str(e)) from e
            raise

        texto = (resp.text or "").strip()
        if not texto:
            raise ValueError("O Gemini não retornou texto (resposta vazia ou bloqueada).")
        return _normalizar(json.loads(texto)), tentativas

    raise GeminiSemApis("Todas as APIs do Gemini estão sobrecarregadas no momento.")


# ======================= GROQ =======================
async def classificar_com_groq(imagem: bytes) -> dict[str, int]:
    bruto = await groq_analisar_imagem(
        image_bytes=imagem,
        prompt=PROMPT_GROQ,
        mime_type="image/png",
    )
    bruto = re.sub(r"<think>.*?</think>", "", bruto or "", flags=re.DOTALL).strip()
    try:
        dados = json.loads(bruto)
    except json.JSONDecodeError:
        achado = re.search(r"\{.*\}", bruto, flags=re.DOTALL)
        if not achado:
            raise ValueError("A Groq não retornou um JSON válido.")
        dados = json.loads(achado.group())
    return _normalizar(dados)


# ======================= ORQUESTRAÇÃO (Gemini -> Groq) =======================
async def classificar_foto(imagem: bytes) -> dict:
    """
    Tenta o Gemini (rodando as APIs); se der 503 ou qualquer outra exceção, tenta a Groq.
    Retorna {"pontuacoes", "provedor", "tentativas_gemini", "motivo_gemini"}.
    Levanta FalhaNasDuasIAs se as duas falharem.
    """
    try:
        pontuacoes, tentativas = await classificar_com_gemini(imagem)
        return {
            "pontuacoes": pontuacoes,
            "provedor": "Gemini",
            "tentativas_gemini": tentativas,
            "motivo_gemini": None,
        }
    except Gemini503 as e:
        motivo_gemini = f"503 (serviço indisponível): {e}"
    except GeminiSemApis as e:
        motivo_gemini = f"sem APIs disponíveis: {e}"
    except Exception as e:
        motivo_gemini = descrever_erro(e)

    try:
        pontuacoes = await classificar_com_groq(imagem)
    except Exception as e:
        raise FalhaNasDuasIAs(motivo_gemini, descrever_erro(e)) from e

    return {
        "pontuacoes": pontuacoes,
        "provedor": "Groq (fallback)",
        "tentativas_gemini": None,
        "motivo_gemini": motivo_gemini,
    }


# ======================= ENVIOS =======================
def _arquivo(imagem: bytes) -> discord.File:
    return discord.File(io.BytesIO(imagem), filename="foto_de_perfil.png")


async def _enviar_em_espera(bot, membro, origem: str, imagem: bytes | None, motivo: str):
    """Nenhuma IA funcionou: manda a foto para a thread de espera, para revisão manual."""
    embed = discord.Embed(
        title="⏳ Foto de perfil em espera",
        description=(
            f"**Membro:** {membro.mention}\n"
            f"**ID:** `{membro.id}`\n"
            f"**Origem:** {ORIGENS.get(origem, origem)}"
        ),
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Motivo", value=f"```{motivo[:900]}```", inline=False)

    kwargs = {}
    if imagem:
        embed.set_image(url="attachment://foto_de_perfil.png")
        kwargs["file"] = _arquivo(imagem)

    try:
        canal = await obter_canal(bot, CHAT_THREAD_LOGS_EM_ESPERA)
        msg_espera = await canal.send(
            embed=embed, allowed_mentions=discord.AllowedMentions.none(), **kwargs
        )
    except discord.HTTPException as e:
        print(f"[PERFIL] Não consegui enviar para a thread de espera: {e}")
        return

    # Agenda a reanálise ("AGENDAR: ANALISAR_PFP", daqui a 10 min).
    # Import tardio: o agendar_analise_pfp importa este arquivo (evita import circular).
    try:
        from sistemas.agendamentos.agendar_analise_pfp import solicitar_agendamento

        await solicitar_agendamento(bot, msg_espera.jump_url, membro.id)
    except Exception as e:
        print(f"[PERFIL] Não consegui agendar a reanálise de {membro.id}: {descrever_erro(e)}")


def _embed_resultado(membro, origem, pontuacoes, provedor, suspeito) -> discord.Embed:
    embed = discord.Embed(
        title="🖼️ Análise de foto de perfil",
        description=(
            f"**Membro:** {membro.mention}\n"
            f"**ID:** `{membro.id}`\n"
            f"**Origem:** {ORIGENS.get(origem, origem)}"
        ),
        color=discord.Color.red() if suspeito else discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )

    for chave, nome in CATEGORIAS.items():
        valor = pontuacoes[chave]
        if valor > LIMITE_PONTOS:
            indicador = "🔴"
        elif valor >= 40:
            indicador = "🟡"
        else:
            indicador = "🟢"
        embed.add_field(name=f"{indicador} {nome}", value=f"`{valor}/100`", inline=True)

    if suspeito:
        embed.add_field(
            name="⚠️ Status",
            value=f"Uma ou mais categorias ultrapassaram `{LIMITE_PONTOS}`.",
            inline=False,
        )
    else:
        embed.add_field(
            name="✅ Status",
            value=f"Nenhuma categoria ultrapassou `{LIMITE_PONTOS}`.",
            inline=False,
        )

    embed.set_image(url="attachment://foto_de_perfil.png")
    embed.set_footer(text=f"Analisado por: {provedor}")
    return embed


async def _enviar_log(bot, embed: discord.Embed, imagem: bytes, view=None):
    kwargs = {"view": view} if view is not None else {}
    try:
        canal = await obter_canal(bot, CHAT_THREAD_LOGS_ANALISE_DE_PERFIL)
        return await canal.send(
            embed=embed,
            file=_arquivo(imagem),
            allowed_mentions=discord.AllowedMentions.none(),
            **kwargs,
        )
    except discord.HTTPException as e:
        print(f"[PERFIL] Não consegui enviar o resultado na thread de logs: {e}")
        return None


# ======================= FUNÇÃO PRINCIPAL =======================
async def analisar_imagem_de_perfil(bot, membro: discord.Member, origem: str, imagem: bytes,
                                    caso_aberto=None):
    """
    Classifica a imagem (Gemini -> Groq), envia o resultado na thread de logs e, se passar de
    LIMITE_PONTOS, abre o tópico de revisão (ou avisa no tópico que já está aberto).
    Levanta FalhaNasDuasIAs se Gemini e Groq falharem (nada é enviado nesse caso).
    Usada por processar_foto e pela reanálise agendada (agendar_analise_pfp.py).
    """
    async with _semaforo:
        resultado = await classificar_foto(imagem)

    pontuacoes = resultado["pontuacoes"]
    provedor = resultado["provedor"]
    suspeitas = {
        CATEGORIAS[k]: v for k, v in pontuacoes.items() if v > LIMITE_PONTOS
    }

    # enviar o resultado (sempre) na thread de logs
    embed = _embed_resultado(membro, origem, pontuacoes, provedor, bool(suspeitas))
    # Botão "Denunciar imagem" só quando o bot NÃO abriu tópico sozinho.
    view = None if suspeitas else DenunciarView(bot)
    msg_log = await _enviar_log(bot, embed, imagem, view)

    if resultado["motivo_gemini"]:
        await log(
            bot,
            "Análise de perfil (Gemini falhou, usada a Groq)",
            f"Membro: {membro} ({membro.id})\nMotivo: `{resultado['motivo_gemini']}`",
        )

    if not suspeitas:
        return

    # segunda parte: passou de 60
    if caso_aberto:
        await avisar_nova_foto_suspeita(caso_aberto, membro, suspeitas)
        return

    try:
        thread = await abrir_caso(bot, membro, imagem, suspeitas)
    except Exception as e:
        print(f"[PERFIL] Erro ao abrir o caso de {membro} ({membro.id}): {e}")
        await log(
            bot,
            "Análise de perfil (erro ao abrir o tópico)",
            f"Membro: {membro} ({membro.id})\nErro: `{descrever_erro(e)}`",
        )
        return

    # liga o log ao tópico de revisão
    if msg_log is not None and thread is not None:
        try:
            embed_log = msg_log.embeds[0]
            embed_log.add_field(name="Tópico de revisão", value=thread.mention, inline=False)
            await msg_log.edit(embed=embed_log)
        except discord.HTTPException:
            pass


async def processar_foto(bot, membro: discord.Member, origem: str):
    """
    origem: "entrada" (entrou no servidor) ou "troca" (trocou a foto).
    """
    # 1) baixar a foto
    try:
        imagem = await baixar_avatar(membro)
    except Exception as e:
        await _enviar_em_espera(
            bot, membro, origem, None, f"Não consegui baixar a foto: {descrever_erro(e)}"
        )
        return

    # 2) se já existe um tópico aberto dessa pessoa, avisa lá que ela trocou de foto
    caso_aberto = None
    if origem == "troca":
        caso_aberto = buscar_caso_aberto(bot, membro.id)
        if caso_aberto:
            await avisar_troca_de_foto(caso_aberto, membro, imagem)

    # 3) analisar, registrar e (se preciso) abrir o tópico
    try:
        await analisar_imagem_de_perfil(bot, membro, origem, imagem, caso_aberto)
    except FalhaNasDuasIAs as e:
        await _enviar_em_espera(
            bot, membro, origem, imagem,
            f"Gemini: {e.motivo_gemini}\nGroq: {e.motivo_groq}",
        )
        await log(
            bot,
            "Análise de perfil (Gemini e Groq falharam)",
            f"Membro: {membro} ({membro.id})\nOrigem: {ORIGENS.get(origem, origem)}\n\n"
            f"Gemini: `{e.motivo_gemini}`\nGroq: `{e.motivo_groq}`\n\n"
            "A foto foi enviada para a thread de espera (reanálise agendada).",
        )