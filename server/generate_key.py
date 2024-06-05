import secrets
import hashlib

def generate_secret_key():
    # Generate a 32-byte secret key using SHA-256 hash
    random_string = secrets.token_hex(32)
    hash_object = hashlib.sha256(random_string.encode())
    return hash_object.hexdigest()

# Generate a secret key
secret_key = generate_secret_key()
print(secret_key)
