"""
Crypto Service for AI Coach
Handles encryption/decryption of Gemini API keys using Fernet (AES-128-CBC)
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Tuple

# Secret key from environment - MUST BE SET IN PRODUCTION
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_SECRET = os.getenv("COACH_ENCRYPTION_SECRET", "development-secret-key-change-in-production")


def _get_fernet() -> Fernet:
    """Get Fernet instance with derived key from secret."""
    # Use PBKDF2 to derive a proper key from the secret
    salt = b"coach_salt_v1"  # Static salt - ok for this use case
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(ENCRYPTION_SECRET.encode()))
    return Fernet(key)


def encrypt_api_key(api_key: str) -> Tuple[bytes, bytes]:
    """
    Encrypt a Gemini API key.
    
    Args:
        api_key: The plaintext API key
        
    Returns:
        Tuple of (encrypted_data, iv) - both as bytes
        Note: Fernet includes IV in the token, but we store separately for clarity
    """
    if not api_key:
        raise ValueError("API key cannot be empty")
    
    fernet = _get_fernet()
    encrypted = fernet.encrypt(api_key.encode())
    
    # Fernet token includes IV, but we extract it for explicit storage
    # First 16 bytes after base64 decode contain the version + timestamp
    # We'll just store the whole token and use empty IV
    return encrypted, b""


def decrypt_api_key(encrypted_data: bytes, iv: bytes = b"") -> Optional[str]:
    """
    Decrypt a Gemini API key.
    
    Args:
        encrypted_data: The encrypted API key
        iv: Initialization vector (unused with Fernet, kept for interface)
        
    Returns:
        The plaintext API key, or None if decryption fails
    """
    if not encrypted_data:
        return None
    
    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(encrypted_data)
        return decrypted.decode()
    except Exception as e:
        print(f"Failed to decrypt API key: {e}")
        return None


def validate_api_key_format(api_key: str) -> bool:
    """
    Validate that an API key looks like a valid Gemini API key.
    Gemini API keys typically start with 'AI' and are 39 characters.
    """
    if not api_key:
        return False
    
    # Basic format check
    # Gemini keys are typically: AIza... (39 chars)
    if len(api_key) < 30:
        return False
    
    # Allow flexibility - just check it's alphanumeric with some special chars
    import re
    if not re.match(r'^[A-Za-z0-9_-]+$', api_key):
        return False
    
    return True


def mask_api_key(api_key: str) -> str:
    """
    Mask an API key for display (show first 4 and last 4 chars).
    """
    if not api_key or len(api_key) < 10:
        return "****"
    
    return f"{api_key[:4]}...{api_key[-4:]}"
