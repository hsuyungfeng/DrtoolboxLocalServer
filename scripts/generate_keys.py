import json
import base64
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def to_base64url(val: int) -> str:
    """Helper to convert integer to base64url string as per JWK spec."""
    # Convert int to bytes, then base64url encode
    byte_len = (val.bit_length() + 7) // 8
    b = val.to_bytes(byte_len, 'big')
    return base64.urlsafe_b64encode(b).decode('utf-8').replace('=', '')

def generate_keys():
    print("🚀 Generating 2048-bit RSA Key Pair...")
    
    # 1. Generate Private Key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # 2. Export Private Key to PEM
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open("private.key", "wb") as f:
        f.write(private_pem)
    print("✅ Private key saved to: private.key (PEM)")

    # 3. Export Public Key to PEM
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open("public.key", "wb") as f:
        f.write(public_pem)
    print("✅ Public key saved to: public.key (PEM)")

    # 4. Generate JWK (JSON Web Key) Format
    # Extract RSA components
    priv_numbers = private_key.private_numbers()
    pub_numbers = public_key.public_numbers()

    # Public JWK
    public_jwk = {
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "n": to_base64url(pub_numbers.n),
        "e": to_base64url(pub_numbers.e),
        "kid": "drtoolbox-key-1" # Key ID
    }

    # Private JWK (Complete set)
    private_jwk = public_jwk.copy()
    private_jwk.update({
        "d": to_base64url(priv_numbers.d),
        "p": to_base64url(priv_numbers.p),
        "q": to_base64url(priv_numbers.q),
        "dp": to_base64url(priv_numbers.dmp1),
        "dq": to_base64url(priv_numbers.dmq1),
        "qi": to_base64url(priv_numbers.iqmp)
    })

    with open("public_jwk.json", "w") as f:
        json.dump(public_jwk, f, indent=4)
    print("✅ Public JWK saved to: public_jwk.json")

    with open("private_jwk.json", "w") as f:
        json.dump(private_jwk, f, indent=4)
    print("✅ Private JWK saved to: private_jwk.json")

    print("\n--- 🔑 PUBLIC JWK (Paste this into LINE/Facebook Console) ---")
    print(json.dumps(public_jwk, indent=4))
    print("-----------------------------------------------------------\n")

if __name__ == "__main__":
    generate_keys()
