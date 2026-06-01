import json
import base64
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def to_base64url(val: int) -> str:
    """Standard JWK base64url encoding."""
    byte_len = (val.bit_length() + 7) // 8
    b = val.to_bytes(byte_len, 'big')
    return base64.urlsafe_b64encode(b).decode('utf-8').replace('=', '')

def generate_jwx_style_keys():
    print("🚀 Replicating 'jwx' tool output logic...")
    
    # 1. Generate RSA 2048 key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    priv_num = private_key.private_numbers()
    pub_num = private_key.public_key().public_numbers()

    # 2. Build Private JWK (private.key)
    # Matching template: {"alg":"RS256","use":"sig"}
    private_jwk = {
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "n": to_base64url(pub_num.n),
        "e": to_base64url(pub_num.e),
        "d": to_base64url(priv_num.d),
        "p": to_base64url(priv_num.p),
        "q": to_base64url(priv_num.q),
        "dp": to_base64url(priv_num.dmp1),
        "dq": to_base64url(priv_num.dmq1),
        "qi": to_base64url(priv_num.iqmp),
        "kid": "drtoolbox-key-2"
    }

    # 3. Build Public JWK (public.key)
    public_jwk = {
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "n": to_base64url(pub_num.n),
        "e": to_base64url(pub_num.e),
        "kid": "drtoolbox-key-2"
    }

    # Save to files with .key extension as requested
    with open("private.key", "w") as f:
        json.dump(private_jwk, f, indent=4)
    print("✅ Created 'private.key' (JSON JWK format)")

    with open("public.key", "w") as f:
        json.dump(public_jwk, f, indent=4)
    print("✅ Created 'public.key' (JSON JWK format)")

    print("\n--- 🔑 CONTENT OF public.key (Paste this) ---")
    print(json.dumps(public_jwk, indent=4))
    print("---------------------------------------------\n")

if __name__ == "__main__":
    generate_jwx_style_keys()
