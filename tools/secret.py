#!/usr/bin/env python3
"""Личните данни на Тетрадката: private/private.json (не влиза в git) <-> private.enc (шифровано, публично).

    python3 tools/secret.py open   # private.enc -> private/private.json
    python3 tools/secret.py seal   # private/private.json -> private.enc

Ключът се взема от променливата TETRADKA_KEY или от файла ~/.tetradka-key.
Никога не се записва в хранилището.
Шифроване: PBKDF2-SHA256 (150 000 итерации) + AES-256-GCM – същото като в index.html (WebCrypto)."""
import base64, json, os, sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENC = os.path.join(ROOT, 'private.enc')
PLAIN = os.path.join(ROOT, 'private', 'private.json')
ITER = 150000


def key_str():
    k = os.environ.get('TETRADKA_KEY')
    if not k:
        p = os.path.expanduser('~/.tetradka-key')
        if os.path.exists(p):
            k = open(p).read().strip()
    if not k:
        sys.exit('Няма ключ: задай TETRADKA_KEY или запиши го в ~/.tetradka-key')
    return k


def derive(k, salt):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(k.encode())


def seal():
    data = json.dumps(json.load(open(PLAIN, encoding='utf-8')), ensure_ascii=False, separators=(',', ':')).encode()
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(derive(key_str(), salt)).encrypt(iv, data, None)
    b = lambda x: base64.b64encode(x).decode()
    json.dump({'v': 1, 'iter': ITER, 'salt': b(salt), 'iv': b(iv), 'ct': b(ct)}, open(ENC, 'w'))
    print('private.enc обновен')


def unseal():
    e = json.load(open(ENC))
    d = base64.b64decode
    pt = AESGCM(derive(key_str(), d(e['salt']))).decrypt(d(e['iv']), d(e['ct']), None)
    os.makedirs(os.path.dirname(PLAIN), exist_ok=True)
    json.dump(json.loads(pt), open(PLAIN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('private/private.json е разшифрован')


if __name__ == '__main__':
    {'seal': seal, 'open': unseal}.get(sys.argv[1] if len(sys.argv) > 1 else '', lambda: sys.exit(__doc__))()
