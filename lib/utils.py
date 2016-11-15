import hmac


def obscure_id(uid, secret, suffix):
    key = bytes(secret, 'utf8') + bytes(suffix, 'utf8')
    message = bytes(uid)
    h = hmac.new(key, message)
    return int.from_bytes(h.digest(), 'little') % 2**63
