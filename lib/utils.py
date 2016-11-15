import hmac
from contextlib import contextmanager


def obscure_id(uid, secret, suffix):
    key = bytes(secret, 'utf8') + bytes(suffix, 'utf8')
    message = bytes(uid)
    h = hmac.new(key, message)
    return int.from_bytes(h.digest(), 'little') % 2**63


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


@contextmanager
def sqlcloser(c):
    try:
        yield c.cursor()
    finally:
        c.commit()

