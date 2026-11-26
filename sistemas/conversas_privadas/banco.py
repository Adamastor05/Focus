from collections import OrderedDict
from itertools import count

LIMITE_LINHAS = 5000  # quantas mensagens ficam lembradas; as mais antigas saem primeiro

_linhas: "OrderedDict[int, dict]" = OrderedDict()
_por_thread: dict[int, int] = {}  # id da msg no tópico -> id da linha
_por_dm: dict[int, int] = {}      # id da msg no privado -> id da linha
_contador = count(1)


def _remover(row_id: int):
    row = _linhas.pop(row_id, None)
    if row:
        _por_thread.pop(row["thread_msg_id"], None)
        _por_dm.pop(row["dm_msg_id"], None)


def salvar(**c):
    for antigo in (_por_thread.get(c["thread_msg_id"]), _por_dm.get(c["dm_msg_id"])):
        if antigo is not None:
            _remover(antigo)

    row_id = next(_contador)
    c["id"] = row_id
    _linhas[row_id] = c
    _por_thread[c["thread_msg_id"]] = row_id
    _por_dm[c["dm_msg_id"]] = row_id

    while len(_linhas) > LIMITE_LINHAS:
        _remover(next(iter(_linhas)))


def por_thread_msg(msg_id: int):
    row_id = _por_thread.get(msg_id)
    return _linhas.get(row_id) if row_id is not None else None


def por_dm_msg(msg_id: int):
    row_id = _por_dm.get(msg_id)
    return _linhas.get(row_id) if row_id is not None else None


def atualizar_conteudo(row_id: int, conteudo: str):
    row = _linhas.get(row_id)
    if row:
        row["conteudo"] = conteudo


def apagar(row_id: int):
    _remover(row_id)