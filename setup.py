"""
setup.py — MediVault first-time setup helper
Run once: python setup.py
Then run the app: python run.py
"""
import os
import sys
import subprocess

def run(cmd, desc):
    print(f"\n▶ {desc}...")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"  ⚠ Warning: '{cmd}' exited with code {result.returncode}")
    else:
        print(f"  ✓ Done")
    return result.returncode

def main():
    print("\n" + "="*60)
    print("  MediVault HMS — First-Time Setup")
    print("="*60)

    # 1. Install dependencies
    run(f"{sys.executable} -m pip install -r requirements.txt",
        "Installing Python dependencies")

    # 2. Create required directories
    for d in ['uploads', 'uploads/reports', 'encrypted', 'decrypted', 'models']:
        os.makedirs(d, exist_ok=True)
    print("\n✓ Created storage directories")

    # 3. Initialize database (creates tables + seeds admin)
    print("\n▶ Initializing database...")
    from app import create_app
    app = create_app()
    with app.app_context():
        from app import db
        db.create_all()
        from models.user import seed_admin
        seed_admin()
    print("  ✓ Database ready (instance/medivault.db)")

    print("\n" + "="*60)
    print("  ✅ Setup complete!")
    print()
    print("  To train the encryption model (OPTIONAL, needs GPU/time):")
    print("    python train_model.py")
    print()
    print("  To start MediVault:")
    print("    python run.py")
    print()
    print("  Login credentials:")
    print("    Email   : admin@medivault.com")
    print("    Password: Admin@1234")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
