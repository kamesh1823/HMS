"""
metrics.py
==========
Image quality and encryption evaluation metrics for MediVault.

Metrics:
  PSNR  — Peak Signal-to-Noise Ratio
          Higher = better reconstruction quality
          For encrypted images: lower PSNR = better encryption (more distortion)
          For decrypted images: higher PSNR = better recovery (≥35 dB is good)

  SSIM  — Structural Similarity Index
          Range: 0 to 1 (1 = identical)
          Encrypted: near 0 = good (structurally unrecognisable)
          Decrypted: near 1 = good (structure well-preserved)

  MSE   — Mean Squared Error
          Lower = more similar; higher = more distortion (good for encryption)

  Entropy — Shannon entropy of pixel intensity distribution
          Range: 0 to 8 (bits per pixel)
          Encrypted image should have entropy close to 8 (random-like distribution)
          Natural images typically have entropy 6–7
"""

import numpy as np
import math


# ── PSNR ───────────────────────────────────────────────────────────

def compute_psnr(img1: np.ndarray, img2: np.ndarray, max_val: float = 1.0) -> float:
    """
    Peak Signal-to-Noise Ratio between two images.

    PSNR = 20 * log10(MAX) - 10 * log10(MSE)

    Args:
        img1, img2: numpy arrays in [0, 1], same shape
        max_val   : maximum possible pixel value (1.0 for normalized)

    Returns:
        PSNR in dB (float). Returns 100.0 if images are identical.
    """
    img1 = np.asarray(img1, dtype=np.float64).flatten()
    img2 = np.asarray(img2, dtype=np.float64).flatten()

    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return 100.0

    psnr = 20 * math.log10(max_val) - 10 * math.log10(mse)
    return round(psnr, 4)


# ── SSIM ───────────────────────────────────────────────────────────

def compute_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Structural Similarity Index (simplified single-window SSIM).

    SSIM(x,y) = (2μxμy + C1)(2σxy + C2) / (μx²+μy²+C1)(σx²+σy²+C2)

    Args:
        img1, img2: numpy arrays in [0, 1], same shape

    Returns:
        SSIM score in [-1, 1] (1 = identical)
    """
    img1 = np.asarray(img1, dtype=np.float64)
    img2 = np.asarray(img2, dtype=np.float64)

    C1 = (0.01) ** 2      # stability constant
    C2 = (0.03) ** 2

    mu1    = img1.mean()
    mu2    = img2.mean()
    sigma1 = img1.std()
    sigma2 = img2.std()
    sigma12= np.mean((img1 - mu1) * (img2 - mu2))

    num = (2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)
    den = (mu1**2 + mu2**2 + C1) * (sigma1**2 + sigma2**2 + C2)

    ssim = num / den
    return round(float(ssim), 6)


# ── MSE ────────────────────────────────────────────────────────────

def compute_mse(img1: np.ndarray, img2: np.ndarray) -> float:
    """Mean Squared Error between two images."""
    img1 = np.asarray(img1, dtype=np.float64).flatten()
    img2 = np.asarray(img2, dtype=np.float64).flatten()
    return round(float(np.mean((img1 - img2) ** 2)), 8)


# ── Entropy ────────────────────────────────────────────────────────

def compute_entropy(img: np.ndarray) -> float:
    """
    Shannon entropy of pixel intensity distribution.

    H = -Σ p(i) * log2(p(i))

    Args:
        img: numpy array in [0, 1]

    Returns:
        Entropy in bits (0 to 8)
    """
    img_uint8 = (np.asarray(img).flatten() * 255).astype(np.uint8)

    # Compute histogram (256 bins)
    hist, _ = np.histogram(img_uint8, bins=256, range=(0, 255))
    hist    = hist.astype(np.float64)

    # Normalize to probability
    total = hist.sum()
    if total == 0:
        return 0.0

    probs = hist[hist > 0] / total

    # Shannon entropy
    entropy = -np.sum(probs * np.log2(probs))
    return round(float(entropy), 4)


# ── Full Evaluation ────────────────────────────────────────────────

def evaluate_encryption(original: np.ndarray,
                          encrypted: np.ndarray,
                          decrypted: np.ndarray = None) -> dict:
    """
    Run all metrics on original vs encrypted (and optionally decrypted).

    Returns:
        dict with all metric values and quality interpretation.
    """
    results = {
        # Encryption quality (original vs encrypted)
        'enc_psnr'   : compute_psnr(original, encrypted),
        'enc_ssim'   : compute_ssim(original, encrypted),
        'enc_mse'    : compute_mse(original, encrypted),
        'enc_entropy': compute_entropy(encrypted),
        'ori_entropy': compute_entropy(original),
    }

    # Interpretation
    results['enc_quality'] = 'Excellent' if results['enc_ssim'] < 0.1 else \
                              'Good'      if results['enc_ssim'] < 0.3 else \
                              'Moderate'

    results['entropy_quality'] = 'Excellent' if results['enc_entropy'] > 7.5 else \
                                   'Good'      if results['enc_entropy'] > 7.0 else \
                                   'Moderate'

    if decrypted is not None:
        results['dec_psnr'] = compute_psnr(original, decrypted)
        results['dec_ssim'] = compute_ssim(original, decrypted)
        results['dec_mse']  = compute_mse(original, decrypted)

        results['dec_quality'] = 'Excellent' if results['dec_psnr'] > 38 else \
                                   'Good'      if results['dec_psnr'] > 30 else \
                                   'Moderate'

    return results
