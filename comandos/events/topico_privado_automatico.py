import asyncio
import discord


async def criar_topico_privado_automatico(
    guild,
    membro,
    obter_ou_criar_chat
):

    # Espera 5 segundos
    await asyncio.sleep(5)

    try:

        thread = await obter_ou_criar_chat(
            guild,
            membro
        )

        print(
            f"[PERDEU PEDIR ACESSO] "
            f"Chat localizado/criado para "
            f"{membro} ({membro.id}) | "
            f"Tópico: {thread.name}"
        )

    except discord.Forbidden:

        print(
            f"[PERDEU PEDIR ACESSO] "
            f"Sem permissão para criar/localizar "
            f"o chat de {membro} ({membro.id})."
        )

    except discord.HTTPException as e:

        print(
            f"[PERDEU PEDIR ACESSO] "
            f"Erro do Discord para {membro} "
            f"({membro.id}): {e}"
        )

    except Exception as e:

        print(
            f"[PERDEU PEDIR ACESSO] "
            f"Erro inesperado para {membro} "
            f"({membro.id}): {e}"
        )