import base64
import json
import secrets
from typing import Any, Optional, Tuple

import secp256k1
from cffi import FFI
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def get_shared_secret(privkey: str, pubkey: str):
    point = secp256k1.PublicKey(bytes.fromhex("02" + pubkey), True)
    return point.ecdh(bytes.fromhex(privkey), hashfn=copy_x)


def decrypt_message(encoded_message: str, encryption_key) -> str:
    encoded_data = encoded_message.split("?iv=")
    if len(encoded_data) == 1:
        return encoded_data[0]
    encoded_content, encoded_iv = encoded_data[0], encoded_data[1]

    iv = base64.b64decode(encoded_iv)
    cipher = Cipher(algorithms.AES(encryption_key), modes.CBC(iv))
    encrypted_content = base64.b64decode(encoded_content)

    decryptor = cipher.decryptor()
    decrypted_message = decryptor.update(encrypted_content) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    unpadded_data = unpadder.update(decrypted_message) + unpadder.finalize()

    return unpadded_data.decode()


def encrypt_message(message: str, encryption_key, iv: Optional[bytes] = None) -> str:
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(message.encode()) + padder.finalize()

    iv = iv if iv else secrets.token_bytes(16)
    cipher = Cipher(algorithms.AES(encryption_key), modes.CBC(iv))

    encryptor = cipher.encryptor()
    encrypted_message = encryptor.update(padded_data) + encryptor.finalize()

    return f"{base64.b64encode(encrypted_message).decode()}?iv={base64.b64encode(iv).decode()}"


def sign_message_hash(private_key: str, hash: bytes) -> str:
    privkey = secp256k1.PrivateKey(bytes.fromhex(private_key))
    sig = privkey.schnorr_sign(hash, None, raw=True)
    return sig.hex()


def test_decrypt_encrypt(encoded_message: str, encryption_key):
    msg = decrypt_message(encoded_message, encryption_key)

    # ecrypt using the same initialisation vector
    iv = base64.b64decode(encoded_message.split("?iv=")[1])
    ecrypted_msg = encrypt_message(msg, encryption_key, iv)
    assert (
        encoded_message == ecrypted_msg
    ), f"expected '{encoded_message}', but got '{ecrypted_msg}'"
    print("### test_decrypt_encrypt", encoded_message == ecrypted_msg)


ffi = FFI()


@ffi.callback(
    "int (unsigned char *, const unsigned char *, const unsigned char *, void *)"
)
def copy_x(output, x32, y32, data):
    ffi.memmove(output, x32, 32)
    return 1


def order_from_json(s: str) -> Tuple[Optional[Any], Optional[str]]:
    try:
        order = json.loads(s)
        return (
            (order, None) if (type(order) is dict) and "items" in order else (None, s)
        )
    except ValueError:
        return None, s
