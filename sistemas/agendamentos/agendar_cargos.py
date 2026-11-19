"""
Ação: CARGOS

Dá ou tira um cargo de uma pessoa, no horário marcado.

Formato:
    AGENDAR: CARGOS
    QUANDO: 18/11/2026 20:57
    Pessoa: <@123456789012345678_>     (obrigatório)
    Cargo: <@&123456789012345678_>     (obrigatório)
    Ação: Adicionar                     (obrigatório)
    Servidor: BIBLIA_EM_FOCO            (opcional)

Pessoa:
    ID, menção (<@id>; escreva com "_>" no fim para não marcar ninguém, o gerenciador
    troca por ">") ou o nome/apelido da pessoa (com ou sem @).

Cargo:
    ID do cargo, menção (<@&id>, também com "_>" no fim) ou o nome do cargo (com ou sem @).

Ação:
    Adicionar  (sinônimos: Add, Dar)
    Remover    (sinônimos: Remove, Tirar)

Servidor (se não for informado, usa SERVIDOR_PADRAO = BIBLIA_EM_FOCO):
    ID do servidor, título do servidor no código (chaves de SERVIDORES)
    ou o nome do servidor no Discord.

Na validação (antes do ✅) o bot confere: se o servidor e o cargo existem, se ele tem
a permissão Gerenciar Cargos, se o cargo está abaixo do maior cargo dele (e não é um
cargo de integração/@everyone) e se a pessoa indicada está no servidor.
"""
import re
import unicodedata

import discord

from config.IDs import BIBLIA_EM_FOCO

# Servidor usado quando o campo "Servidor" não é informado.
SERVIDOR_PADRAO = BIBLIA_EM_FOCO

# Título do servidor no código -> ID. Para aceitar outros servidores, é só acrescentar aqui.
SERVIDORES = {
    "BIBLIA_EM_FOCO": BIBLIA_EM_FOCO,
}

_ACOES = {
    "adicionar": "adicionar", "add": "adicionar", "dar": "adicionar",
    "remover": "remover", "remove": "remover", "tirar": "remover",
}


def _norm(texto) -> str:
    """Minúsculas, sem acentos e com espaços normalizados (para comparar nomes)."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.casefold().split())


def _chave_servidor(texto) -> str:
    return _norm(texto).replace(" ", "_")


# ---------------------------------------------------------------- resolução
def _resolver_servidor(bot, valor: str):
    """Retorna (guild, erro)."""
    valor = (valor or "").strip()

    if not valor:
        guild_id = SERVIDOR_PADRAO
    elif re.fullmatch(r"\d{15,20}", valor):
        guild_id = int(valor)
    else:
        titulos = {_chave_servidor(k): v for k, v in SERVIDORES.items()}
        guild_id = titulos.get(_chave_servidor(valor))
        if guild_id is None:  # por último, tenta o nome real do servidor no Discord
            iguais = [g for g in bot.guilds if _norm(g.name) == _norm(valor)]
            if len(iguais) == 1:
                return iguais[0], None
            if len(iguais) > 1:
                return None, f"Existe mais de um servidor chamado `{valor}`. Use o ID."
            conhecidos = ", ".join(f"`{k}`" for k in SERVIDORES)
            return None, f"Servidor `{valor}` não encontrado. Use o ID ou um destes títulos: {conhecidos}."

    guild = bot.get_guild(int(guild_id))
    if guild is None:
        return None, f"O bot não está no servidor `{guild_id}`."
    return guild, None


def _resolver_cargo(guild, valor: str):
    """Retorna (cargo, erro)."""
    achado = re.search(r"\d{15,20}", valor)
    if achado:
        cargo = guild.get_role(int(achado.group()))
        if cargo is None:
            return None, f"O cargo `{achado.group()}` não existe no servidor **{guild.name}**."
        return cargo, None

    nome = _norm(valor.strip().lstrip("@"))
    if not nome:
        return None, "Campo `Cargo` inválido. Use o ID, a menção ou o nome do cargo."
    iguais = [r for r in guild.roles if _norm(r.name) == nome]
    if not iguais:
        return None, f"Não achei um cargo chamado `{valor.strip()}` no servidor **{guild.name}**."
    if len(iguais) > 1:
        return None, f"Existe mais de um cargo chamado `{valor.strip()}`. Use o ID do cargo."
    return iguais[0], None


def _checar_permissoes(guild, cargo):
    """Retorna uma mensagem de erro, ou None se o bot pode dar/tirar esse cargo."""
    me = guild.me
    if me is None:
        return f"O bot não foi encontrado como membro do servidor **{guild.name}**."
    if not me.guild_permissions.manage_roles:
        return f"O bot não tem a permissão **Gerenciar Cargos** no servidor **{guild.name}**."
    if cargo.is_default():
        return "O cargo @everyone não pode ser dado nem removido."
    if cargo.managed:
        return (
            f"O cargo **{cargo.name}** é gerenciado por uma integração (bot, booster...) "
            "e não pode ser dado nem removido manualmente."
        )
    if cargo.position >= me.top_role.position:
        return (
            f"O cargo **{cargo.name}** está acima (ou no mesmo nível) do maior cargo do bot, "
            "então o bot não consegue gerenciá-lo."
        )
    return None


async def _resolver_pessoa(guild, valor: str):
    """Retorna (membro, erro). A pessoa vem do campo `Pessoa`."""
    achado = re.search(r"\d{15,20}", valor)
    if achado:
        pessoa_id = int(achado.group())
        membro = guild.get_member(pessoa_id)
        if membro is None:
            try:
                membro = await guild.fetch_member(pessoa_id)
            except discord.NotFound:
                return None, f"A pessoa `{pessoa_id}` não está no servidor **{guild.name}**."
            except discord.HTTPException as e:
                return None, f"Não foi possível consultar a pessoa no servidor **{guild.name}**: {e}"
        return membro, None

    nome = _norm(valor.strip().lstrip("@"))
    if not nome:
        return None, "Campo `Pessoa` inválido. Use o ID ou a menção da pessoa."
    iguais = [
        m for m in guild.members
        if nome in {_norm(x) for x in (m.name, m.display_name, getattr(m, "global_name", None)) if x}
    ]
    if not iguais:
        return None, f"Não achei `{valor.strip()}` no servidor **{guild.name}**. Use o ID ou a menção da pessoa."
    if len(iguais) > 1:
        return None, f"Existe mais de uma pessoa chamada `{valor.strip()}`. Use o ID ou a menção."
    return iguais[0], None


async def _resolver(bot, dados):
    """Retorna ((guild, cargo, membro, acao), erro)."""
    campos = dados["campos"]

    bruto_acao = campos.get("AÇÃO") or campos.get("ACAO") or ""
    if not bruto_acao:
        return None, "Falta o campo `Ação` (`Adicionar` ou `Remover`)."
    acao = _ACOES.get(_norm(bruto_acao))
    if acao is None:
        return None, "`Ação` inválida. Use `Adicionar` (Add, Dar) ou `Remover` (Remove, Tirar)."

    valor_cargo = campos.get("CARGO", "")
    if not valor_cargo:
        return None, "Falta o campo `Cargo` (ID, menção ou nome do cargo)."

    valor_pessoa = campos.get("PESSOA", "")
    if not valor_pessoa:
        return None, "Falta o campo `Pessoa` (ID, menção ou nome)."

    guild, erro = _resolver_servidor(bot, campos.get("SERVIDOR", ""))
    if erro:
        return None, erro

    cargo, erro = _resolver_cargo(guild, valor_cargo)
    if erro:
        return None, erro

    erro = _checar_permissoes(guild, cargo)
    if erro:
        return None, erro

    membro, erro = await _resolver_pessoa(guild, valor_pessoa)
    if erro:
        return None, erro

    return (guild, cargo, membro, acao), None


# ---------------------------------------------------------------- execução
async def executar(bot, dados, validar=False):
    contexto, erro = await _resolver(bot, dados)

    if validar:
        return erro  # None = formato e permissões corretos

    if erro:
        raise RuntimeError(erro)

    guild, cargo, membro, acao = contexto
    tem_o_cargo = any(r.id == cargo.id for r in membro.roles)
    quem_pediu = dados.get("autor_id")
    razao = f"Agendamento solicitado por {quem_pediu}" if quem_pediu else "Agendamento"

    # O texto retornado aparece como "Resultado" no log de execuções.
    if acao == "adicionar":
        if tem_o_cargo:
            return f"{membro} já tinha o cargo **{cargo.name}** em {guild.name}; nada mudou."
        await membro.add_roles(cargo, reason=razao)
        return f"Cargo **{cargo.name}** adicionado a {membro} em {guild.name}."

    if not tem_o_cargo:
        return f"{membro} não tinha o cargo **{cargo.name}** em {guild.name}; nada mudou."
    await membro.remove_roles(cargo, reason=razao)
    return f"Cargo **{cargo.name}** removido de {membro} em {guild.name}."