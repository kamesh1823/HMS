"""
train_model.py
==============
Train the CNN Autoencoder on medical images.

Usage:
    python train_model.py

What this does:
  1. Loads all images from ./dataset/ folder
  2. Preprocesses them to 224×224 grayscale
  3. Trains the autoencoder (input = output, unsupervised)
  4. Saves the encoder and decoder to ./models/

Dataset:
  - Place Brain MRI images (PNG/JPG) inside the ./dataset/ folder
  - Download from: https://www.kaggle.com/datasets/navoneel/brain-mri-images-for-brain-tumor-detection
  - Or use any grayscale medical images (X-ray, MRI, CT)
  - Minimum recommended: 100 images (more = better reconstruction)

Training time:
  - CPU  : ~10-20 minutes for 200 images, 20 epochs
  - GPU  : ~2-5  minutes
"""

import os
import sys
import numpy as np
from PIL import Image

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encryption.autoencoder import (
    build_autoencoder, save_model, IMG_SIZE, MODEL_PATH
)

# ── Config ─────────────────────────────────────────────────────────
DATASET_DIR = os.path.join(os.path.dirname(__file__), 'dataset')
EPOCHS      = 30
BATCH_SIZE  = 16
VALID_SPLIT = 0.15
EXTENSIONS  = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')


# ── Load Dataset ───────────────────────────────────────────────────

def load_dataset(dataset_dir: str) -> np.ndarray:
    """
    Load all images from dataset directory.
    Converts to grayscale, resizes to 224×224, normalizes to [0,1].
    Returns numpy array of shape (N, 224, 224, 1).
    """
    images = []
    valid_ext = EXTENSIONS

    all_files = []
    for root, _, files in os.walk(dataset_dir):
        for f in files:
            if f.lower().endswith(valid_ext):
                all_files.append(os.path.join(root, f))

    if not all_files:
        raise ValueError(
            f"No images found in {dataset_dir}!\n"
            f"Please add medical images (PNG/JPG) to the dataset/ folder."
        )

    print(f"[→] Found {len(all_files)} images in dataset/")

    for i, fpath in enumerate(all_files):
        try:
            img = Image.open(fpath).convert('L')
            img = img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
            arr = np.array(img, dtype=np.float32) / 255.0
            images.append(arr)
        except Exception as e:
            print(f"   [!] Skipping {fpath}: {e}")

        if (i + 1) % 50 == 0:
            print(f"   Loaded {i+1}/{len(all_files)} images…")

    data = np.array(images, dtype=np.float32)
    data = data.reshape(-1, IMG_SIZE, IMG_SIZE, 1)
    print(f"[✓] Dataset shape: {data.shape}")
    return data


# ── Training Callback ──────────────────────────────────────────────

class TrainingProgress:
    """Simple callback to show progress."""
    def __init__(self):
        self.losses = []

    def on_epoch_end(self, epoch, logs=None):
        loss     = logs.get('loss', 0)
        val_loss = logs.get('val_loss', 0)
        self.losses.append(loss)
        print(f"   Epoch {epoch+1:3d} | loss: {loss:.6f} | val_loss: {val_loss:.6f}")


# ── Demo with Synthetic Data (if no dataset) ───────────────────────

def generate_synthetic_data(n=50):
    """
    Generate synthetic grayscale images for demo/testing.
    Creates random gradient patterns resembling MRI-like images.
    Use this ONLY if you don't have real medical images.
    """
    print("[!] No dataset found. Generating synthetic demo data (50 images).")
    print("    For real results, add MRI images to the dataset/ folder.")

    images = []
    for i in range(n):
        # Create gradient + noise image simulating MRI appearance
        x = np.linspace(0, 1, IMG_SIZE)
        y = np.linspace(0, 1, IMG_SIZE)
        xx, yy = np.meshgrid(x, y)

        # Random circular blob (simulate brain scan)
        cx, cy = np.random.uniform(0.3, 0.7, 2)
        r      = np.random.uniform(0.2, 0.4)
        circle = np.exp(-((xx - cx)**2 + (yy - cy)**2) / (2 * r**2))

        # Add noise
        noise  = np.random.normal(0, 0.05, (IMG_SIZE, IMG_SIZE))
        img    = np.clip(circle + noise, 0, 1).astype(np.float32)
        images.append(img)

    data = np.array(images).reshape(-1, IMG_SIZE, IMG_SIZE, 1)
    print(f"[✓] Synthetic dataset shape: {data.shape}")
    return data


# ── Main Training ──────────────────────────────────────────────────

def train():
    import tensorflow as tf

    print("=" * 60)
    print("  MediVault — CNN Autoencoder Training")
    print("=" * 60)
    print(f"  TensorFlow version : {tf.__version__}")
    print(f"  Dataset directory  : {DATASET_DIR}")
    print(f"  Image size         : {IMG_SIZE}×{IMG_SIZE}")
    print(f"  Epochs             : {EPOCHS}")
    print(f"  Batch size         : {BATCH_SIZE}")
    print("=" * 60)

    # Load data
    os.makedirs(DATASET_DIR, exist_ok=True)
    try:
        data = load_dataset(DATASET_DIR)
    except ValueError:
        data = generate_synthetic_data(n=100)

    # Shuffle
    idx  = np.random.permutation(len(data))
    data = data[idx]

    # Build model
    print("\n[→] Building autoencoder architecture…")
    autoencoder, encoder, decoder = build_autoencoder()
    autoencoder.summary()

    # Callbacks
    import tensorflow as tf
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_loss', patience=5, restore_best_weights=True, verbose=1
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss', factor=0.5, patience=3, verbose=1
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=MODEL_PATH.replace('.keras', '_best.keras'),
            monitor='val_loss', save_best_only=True, verbose=0
        ),
    ]

    # Train (unsupervised: input = target)
    print(f"\n[→] Training on {len(data)} images…\n")
    history = autoencoder.fit(
        data, data,                  # X = Y (reconstruction task)
        epochs          = EPOCHS,
        batch_size      = BATCH_SIZE,
        validation_split= VALID_SPLIT,
        callbacks       = callbacks,
        verbose         = 1,
    )

    # Save models
    print("\n[→] Saving models…")
    save_model(autoencoder, encoder, decoder)

    # Final stats
    final_loss = history.history['loss'][-1]
    print(f"\n{'='*60}")
    print(f"  Training complete!")
    print(f"  Final training loss : {final_loss:.6f}")
    print(f"  Models saved to     : ./models/")
    print(f"\n  You can now use the system to encrypt/decrypt medical images.")
    print(f"{'='*60}\n")

    return history


if __name__ == '__main__':
    train()
