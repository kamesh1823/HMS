"""
run.py — MediVault HMS entry point
Run with: python run.py
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    print("\n" + "="*55)
    print("  MediVault HMS — Starting server...")
    print("  Open: http://127.0.0.1:5000")
    print("  Admin login : admin@medivault.com")
    print("  Password    : Admin@1234")
    print("="*55 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
