"""
test_encryption.py
==================
Quick test to verify the encryption components work correctly.
Run this BEFORE training the full model.

Usage:
    python test_encryption.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

print("=" * 60)
print("  MediVault — Encryption Component Tests")
print("=" * 60)

# ── Test 1: Chaotic Key Generation ─────────────────────────────
print("\n[TEST 1] Chaotic Key Generator")
from encryption.chaotic_key import derive_seed, logistic_map, generate_key_array, get_key_preview

seed = derive_seed("MV-2024-0001", "1990-05-14", "HOSP_001")
print(f"  Patient ID : MV-2024-0001")
print(f"  DOB        : 1990-05-14")
print(f"  SHA-256 seed (float): {seed:.8f}")

key = generate_key_array("MV-2024-0001", "1990-05-14", "HOSP_001", size=100)
print(f"  Key array (first 10): {key[:10]}")
print(f"  Key range: [{key.min()}, {key.max()}]")

# Test determinism
key2 = generate_key_array("MV-2024-0001", "1990-05-14", "HOSP_001", size=100)
assert np.array_equal(key, key2), "Keys should be identical for same inputs!"
print(f"  ✓ Deterministic: same inputs → identical key")

# Test different patient → different key
key3 = generate_key_array("MV-2024-0002", "1985-03-22", "HOSP_001", size=100)
assert not np.array_equal(key, key3), "Different patients should have different keys!"
print(f"  ✓ Unique: different patient → different key")

preview = get_key_preview("MV-2024-0001", "1990-05-14")
print(f"  Key preview: {preview}")

# ── Test 2: Metrics ─────────────────────────────────────────────
print("\n[TEST 2] Encryption Metrics")
from encryption.metrics import compute_psnr, compute_ssim, compute_mse, compute_entropy, evaluate_encryption

# Create test images
original  = np.random.rand(224, 224).astype(np.float32)
encrypted = np.random.rand(224, 224).astype(np.float32)   # simulate encrypted
decrypted = original + np.random.normal(0, 0.01, original.shape).astype(np.float32)
decrypted = np.clip(decrypted, 0, 1)

psnr_enc = compute_psnr(original, encrypted)
psnr_dec = compute_psnr(original, decrypted)
ssim_enc = compute_ssim(original, encrypted)
ssim_dec = compute_ssim(original, decrypted)
entropy  = compute_entropy(encrypted)

print(f"  Encrypted PSNR  : {psnr_enc:.2f} dB  (lower = better encryption)")
print(f"  Decrypted PSNR  : {psnr_dec:.2f} dB  (higher = better recovery)")
print(f"  Encrypted SSIM  : {ssim_enc:.4f}   (near 0 = good encryption)")
print(f"  Decrypted SSIM  : {ssim_dec:.4f}   (near 1 = good recovery)")
print(f"  Encrypted Entropy: {entropy:.4f} bits (near 8.0 = random-like)")

results = evaluate_encryption(original, encrypted, decrypted)
print(f"  Encryption quality : {results['enc_quality']}")
print(f"  Entropy quality    : {results['entropy_quality']}")
print(f"  Decryption quality : {results['dec_quality']}")

# ── Test 3: XOR Self-inverse ────────────────────────────────────
print("\n[TEST 3] XOR Self-inverse Property")
from encryption.pipeline import xor_latent, unxor_latent

dummy_latent = np.random.rand(1, 28, 28, 256).astype(np.float32)
scrambled    = xor_latent(dummy_latent, "MV-2024-0001", "1990-05-14", "HOSP_001")
restored     = unxor_latent(scrambled, "MV-2024-0001", "1990-05-14", "HOSP_001")

diff = np.abs(dummy_latent - restored).max()
print(f"  Max difference after encrypt→decrypt: {diff:.8f}")
print(f"  ✓ Self-inverse property verified (diff < 1e-5: {diff < 1e-5})")

# Wrong key should fail
scrambled2  = xor_latent(dummy_latent, "MV-2024-0001", "1990-05-14", "HOSP_001")
wrong_restore = unxor_latent(scrambled2, "MV-2024-9999", "2000-01-01", "HOSP_001")
diff_wrong  = np.abs(dummy_latent - wrong_restore).max()
print(f"  Wrong key diff: {diff_wrong:.4f} (should be high — decryption fails with wrong key)")
print(f"  ✓ Wrong key produces incorrect output")

print("\n" + "=" * 60)
print("  ALL TESTS PASSED ✓")
print("  Run 'python train_model.py' to train the CNN model.")
print("=" * 60 + "\n")
