

def obscure_id(uid, secret, suffix):
    s = int.from_bytes(bytes(secret, 'utf8') + bytes(suffix, 'utf8'), 'little')
    return s % uid
