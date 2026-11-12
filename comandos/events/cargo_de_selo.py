import discord
from discord.ext import commands

from config.IDs import CARGO_HOMEM, CARGO_AF, CARGO_GENERO_NAO_INFORMADO, CARGO_DISCIPULOS, CARGO_FORASTEIROS

# Esse comando vê quais cargos a pessoa GANHOU, e ADICIONA OU REMOVE algum outro cargo dela.

# Mapeamento das regras:
# ID do cargo ganho : {"adicionar": [IDs], "remover": [IDs]}
REGRAS_CARGOS = {
            CARGO_HOMEM: {
                "adicionar": [CARGO_AF],
                "remover": []
            },
            CARGO_GENERO_NAO_INFORMADO: {
                "adicionar": [CARGO_AF],
                "remover": []    
            },
            CARGO_DISCIPULOS: {
                "adicionar": [],
                "remover": [CARGO_FORASTEIROS]
            }
        }

async def processar_cargo_de_selo(before: discord.Member, after: discord.Member):
    # Ignora se a alteração não foi nos cargos
    if before.roles == after.roles:
        return

    cargos_adicionados = set(after.roles) - set(before.roles)

    for cargo in cargos_adicionados:
        if cargo.id in REGRAS_CARGOS:
            regra = REGRAS_CARGOS[cargo.id]

            # 1. Adiciona os cargos configurados
            for id_add in regra["adicionar"]:
                cargo_add = after.guild.get_role(id_add)
                if cargo_add and cargo_add not in after.roles:
                    try:
                        await after.add_roles(cargo_add, reason="Cargo de selo automático")
                    except discord.Forbidden:
                        print(f"Sem permissão para adicionar {cargo_add.name}")

            # 2. Remove os cargos configurados
            for id_rem in regra["remover"]:
                cargo_rem = after.guild.get_role(id_rem)
                if cargo_rem and cargo_rem in after.roles:
                    try:
                        await after.remove_roles(cargo_rem, reason="Regra automática: Perder cargo")
                    except discord.Forbidden:
                        print(f"Sem permissão para remover {cargo_rem.name}")