import base64
import secrets

import coincurve
from bech32 import bech32_decode, convertbits
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def get_shared_secret(privkey: str, pubkey: str):
    pk = coincurve.PublicKey(bytes.fromhex("02" + pubkey))
    sk = coincurve.PrivateKey(bytes.fromhex(privkey))
    shared_point = pk.multiply(sk.secret)

    shared_point_bytes = shared_point.format(compressed=False)
    x_coord = shared_point_bytes[1:33]
    return x_coord


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


def encrypt_message(message: str, encryption_key, iv: bytes | None = None) -> str:
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(message.encode()) + padder.finalize()

    iv = iv if iv else secrets.token_bytes(16)
    cipher = Cipher(algorithms.AES(encryption_key), modes.CBC(iv))

    encryptor = cipher.encryptor()
    encrypted_message = encryptor.update(padded_data) + encryptor.finalize()

    base64_message = base64.b64encode(encrypted_message).decode()
    base64_iv = base64.b64encode(iv).decode()
    return f"{base64_message}?iv={base64_iv}"


def sign_message_hash(private_key: str, hash_: bytes) -> str:
    privkey = coincurve.PrivateKey(bytes.fromhex(private_key))
    sig = privkey.sign_schnorr(hash_)
    return sig.hex()


def test_decrypt_encrypt(encoded_message: str, encryption_key):
    msg = decrypt_message(encoded_message, encryption_key)

    # ecrypt using the same initialisation vector
    iv = base64.b64decode(encoded_message.split("?iv=")[1])
    ecrypted_msg = encrypt_message(msg, encryption_key, iv)
    assert (
        encoded_message == ecrypted_msg
    ), f"expected '{encoded_message}', but got '{ecrypted_msg}'"


def normalize_public_key(pubkey: str) -> str:
    if pubkey.startswith("npub1"):
        _, decoded_data = bech32_decode(pubkey)
        if not decoded_data:
            raise ValueError("Public Key is not valid npub")

        decoded_data_bits = convertbits(decoded_data, 5, 8, False)
        if not decoded_data_bits:
            raise ValueError("Public Key is not valid npub")
        return bytes(decoded_data_bits).hex()

    # check if valid hex
    if len(pubkey) != 64:
        raise ValueError("Public Key is not valid hex")
    int(pubkey, 16)
    return pubkey
