"""
chaotic_key.py
==============
Deterministic encryption key derivation for MediVault.

Flow:
    Patient ID + DOB + Hospital ID
        → SHA-256 hash
        → float seed in (0,1)
        → Logistic Map iterations
        → byte key array  (same length as image pixels)
        → XOR with image pixel data  →  encrypted image

Security properties:
  • Fully deterministic  → same inputs always produce same key
  • No password stored   → key re-derived on every access
  • Chaotic sensitivity  → tiny change in inputs = completely different key
  • SHA-256 pre-hashing  → cryptographically strong seed generation
"""

import hashlib
import numpy as np


# ── Key Derivation ──────────────────────────────────────────────────

def derive_seed(patient_id: str, date_of_birth: str, hospital_id: str = "HOSP_001") -> float:
    """
    Derive a float seed in (0, 1) from patient metadata using SHA-256.

    Args:
        patient_id   : e.g. "MV-2024-0001"
        date_of_birth: e.g. "1990-05-14"
        hospital_id  : e.g. "HOSP_001"

    Returns:
        float in range (0.3, 0.7)  — safe range for logistic map chaos
    """
    raw = f"{patient_id}{date_of_birth}{hospital_id}"
    hash_hex = hashlib.sha256(raw.encode('utf-8')).hexdigest()

    # Take first 16 hex chars → 64-bit integer → normalize to (0,1)
    hash_int = int(hash_hex[:16], 16)
    seed = hash_int / (16 ** 16)          # normalize to (0,1)

    # Clamp to (0.3, 0.7) — chaos zone of logistic map
    seed = 0.3 + (seed % 0.4)
    return seed


def logistic_map(seed: float, size: int, r: float = 3.99) -> np.ndarray:
    """
    Generate a chaotic sequence using the logistic map.

    Logistic map equation: x_{n+1} = r * x_n * (1 - x_n)
    At r ≈ 3.99 the sequence is fully chaotic and non-repeating.

    Args:
        seed : initial value x_0 ∈ (0, 1)
        size : number of values to generate
        r    : chaos parameter (default 3.99 for full chaos)

    Returns:
        np.ndarray of float values in (0, 1), shape (size,)
    """
    sequence = np.zeros(size, dtype=np.float64)
    x = seed

    # Warm up the map to discard transient behaviour (first 500 iterations)
    for _ in range(500):
        x = r * x * (1.0 - x)

    for i in range(size):
        x = r * x * (1.0 - x)
        sequence[i] = x

    return sequence


def generate_key_array(patient_id: str,
                        date_of_birth: str,
                        hospital_id: str,
                        size: int) -> np.ndarray:
    """
    Full pipeline: metadata → SHA-256 seed → logistic map → byte key.

    Args:
        patient_id   : Patient ID string
        date_of_birth: DOB string "YYYY-MM-DD"
        hospital_id  : Hospital identifier
        size         : Total number of pixels (H × W × C)

    Returns:
        np.ndarray of uint8 values in [0, 255], shape (size,)
    """
    seed     = derive_seed(patient_id, date_of_birth, hospital_id)
    sequence = logistic_map(seed, size)

    # Map (0,1) floats → [0,255] integers
    key_bytes = (sequence * 255).astype(np.uint8)
    return key_bytes


def get_key_preview(patient_id: str, date_of_birth: str, hospital_id: str = "HOSP_001") -> str:
    """Return first 32 chars of SHA-256 hash for UI display."""
    raw = f"{patient_id}{date_of_birth}{hospital_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32] + "…"
