"""
pipeline.py
===========
MediVault Encryption / Decryption Pipeline

Encryption Flow:
  1. Load & preprocess image  → (224,224) uint8 array
  2. Generate chaotic key     → same-size byte array from patient metadata
  3. XOR pixels with key      → encrypted image (visually scrambled)
  4. Save encrypted image as PNG

Decryption Flow:
  1. Load encrypted image     → (224,224) uint8 array
  2. Re-derive the SAME chaotic key (same patient metadata → same seed → same key)
  3. XOR encrypted pixels with key again → original pixels restored
     (XOR self-inverse: A⊕K⊕K = A)
  4. Save decrypted image

Why this works perfectly:
  Encrypt:  E[i] = P[i] XOR K[i]
  Decrypt:  P[i] = E[i] XOR K[i]   ← same key, perfect reversal
"""

import os
import numpy as np
from PIL import Image

from encryption.chaotic_key import generate_key_array
from encryption.autoencoder import load_models, models_exist

# Image target size
IMG_SIZE = 224


# ── Image helpers ──────────────────────────────────────────────────

def load_image_uint8(path: str) -> np.ndarray:
    """Load image, convert to grayscale, resize to 224×224. Returns uint8 array."""
    img = Image.open(path).convert('L')
    img = img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
    return np.array(img, dtype=np.uint8)


def save_image_uint8(arr: np.ndarray, path: str):
    """Save a (224,224) uint8 array as PNG."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Image.fromarray(arr.astype(np.uint8), mode='L').save(path)


def load_image(path: str) -> np.ndarray:
    """Load image normalized to [0,1] float32 for metric computation."""
    arr = load_image_uint8(path)
    return arr.reshape(1, IMG_SIZE, IMG_SIZE, 1).astype(np.float32) / 255.0


def save_image(arr: np.ndarray, path: str):
    """Save a (1,224,224,1) float32 array as PNG."""
    img_data = (arr.squeeze() * 255).clip(0, 255).astype(np.uint8)
    save_image_uint8(img_data, path)


# ── Pixel-space chaotic XOR (perfectly invertible) ─────────────────

def xor_pixels(pixels: np.ndarray,
               patient_id: str,
               date_of_birth: str,
               hospital_id: str) -> np.ndarray:
    """
    XOR every pixel with the chaotic key byte.
    Works for both encryption AND decryption (self-inverse).

    Args:
        pixels       : uint8 array shape (224, 224)
        patient_id   : for key derivation
        date_of_birth: for key derivation
        hospital_id  : for key derivation

    Returns:
        XOR'd uint8 array (same shape) — encrypted or decrypted
    """
    flat_size = pixels.size                          # 224 × 224 = 50176
    key_bytes = generate_key_array(patient_id, date_of_birth, hospital_id, flat_size)

    # True integer XOR — perfectly invertible
    result = np.bitwise_xor(pixels.flatten(), key_bytes[:flat_size])
    return result.reshape(pixels.shape).astype(np.uint8)


# ── Main Encrypt ───────────────────────────────────────────────────

def encrypt_image(image_path: str,
                  output_path: str,
                  patient_id: str,
                  date_of_birth: str,
                  hospital_id: str = "HOSP_001") -> dict:
    """
    Encrypt a medical image using chaotic pixel-space XOR.

    Returns dict with metrics: psnr, entropy, status
    """
    from encryption.metrics import compute_psnr, compute_ssim, compute_entropy

    try:
        # 1. Load original image as uint8
        original_u8  = load_image_uint8(image_path)          # (224, 224) uint8

        # 2. XOR with chaotic key → encrypted pixels
        encrypted_u8 = xor_pixels(original_u8, patient_id, date_of_birth, hospital_id)

        # 3. Save encrypted image
        save_image_uint8(encrypted_u8, output_path)

        # 4. Compute metrics (float [0,1] scale)
        orig_f  = original_u8.astype(np.float32)  / 255.0
        enc_f   = encrypted_u8.astype(np.float32) / 255.0

        metrics = {
            'status'                     : 'success',
            'psnr_original_vs_encrypted' : compute_psnr(orig_f, enc_f),
            'entropy_encrypted'          : compute_entropy(enc_f),
            'message'                    : 'Image encrypted successfully.',
        }
        return metrics

    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# ── Main Decrypt ───────────────────────────────────────────────────

def decrypt_image(encrypted_path: str,
                  output_path: str,
                  patient_id: str,
                  date_of_birth: str,
                  hospital_id: str = "HOSP_001") -> dict:
    """
    Decrypt a medical image — XOR with the same key reverses encryption perfectly.

    Returns dict with metrics and status
    """
    from encryption.metrics import compute_psnr, compute_ssim, compute_entropy

    try:
        # 1. Load encrypted image as uint8
        encrypted_u8  = load_image_uint8(encrypted_path)     # (224, 224) uint8

        # 2. XOR with same key → original pixels restored (A⊕K⊕K = A)
        decrypted_u8  = xor_pixels(encrypted_u8, patient_id, date_of_birth, hospital_id)

        # 3. Save decrypted image
        save_image_uint8(decrypted_u8, output_path)

        # 4. Compute quality metrics
        enc_f  = encrypted_u8.astype(np.float32)  / 255.0
        dec_f  = decrypted_u8.astype(np.float32)  / 255.0

        metrics = {
            'status'  : 'success',
            'psnr'    : compute_psnr(enc_f, dec_f),
            'entropy' : compute_entropy(dec_f),
            'message' : 'Image decrypted successfully — original restored.',
        }
        return metrics

    except Exception as e:
        return {'status': 'error', 'message': str(e)}
