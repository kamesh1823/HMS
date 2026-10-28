# 🏥 MediVault HMS
### Privacy-Preserving Hospital Management System with AI-Powered Medical Image Encryption

---

## 🚀 Quick Start (Offline Hosting)

### Step 1 — Prerequisites
- Python 3.10 or 3.11 recommended
- pip (comes with Python)

### Step 2 — Setup (Run Once)
```bash
cd medivault
python setup.py
```
This installs all dependencies, creates the database, and seeds the default admin account.

### Step 3 — Start the Server
```bash
python run.py
```
Open your browser → **http://127.0.0.1:5000**

---

## 🔐 Default Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@medivault.com | Admin@1234 |

> The admin can create additional users (doctors, radiologists, receptionists) from **Admin → Manage Users**.

---

## 📁 Project Structure

```
medivault/
├── run.py                  ← Start the app
├── setup.py                ← First-time setup
├── app.py                  ← Flask application factory
├── train_model.py          ← Train CNN autoencoder (optional)
├── test_encryption.py      ← Test encryption pipeline
├── requirements.txt        ← Python dependencies
│
├── models/                 ← SQLAlchemy database models
│   ├── user.py             ← User, roles, auth
│   └── patient.py          ← Patient, Visit, Scan, Prescription, etc.
│
├── routes/                 ← Flask blueprints (URL handlers)
│   ├── main.py             ← Homepage + appointment booking API
│   ├── auth.py             ← Login / Logout
│   ├── dashboard.py        ← Role-based dashboards
│   ├── patients.py         ← Patient CRUD + visit management
│   ├── scans.py            ← Medical scan upload/encrypt/decrypt
│   ├── appointments.py     ← Appointment management
│   ├── reports.py          ← Lab report upload/download
│   ├── metrics_route.py    ← Encryption metrics dashboard
│   └── admin.py            ← User management + audit log
│
├── encryption/             ← AI encryption core
│   ├── pipeline.py         ← Encrypt/decrypt pipeline
│   ├── chaotic_key.py      ← Logistic map key derivation
│   ├── autoencoder.py      ← CNN autoencoder model
│   └── metrics.py          ← PSNR, SSIM, Entropy, MSE
│
├── templates/              ← Jinja2 HTML templates
│   ├── base.html           ← Master layout with sidebar
│   ├── index.html          ← Public homepage
│   ├── auth/               ← Login page
│   ├── dashboard/          ← Role dashboards
│   ├── patients/           ← Patient management pages
│   ├── scans/              ← Scan upload/view pages
│   ├── appointments/       ← Appointment pages
│   ├── reports/            ← Lab report pages
│   ├── metrics/            ← Metrics dashboard
│   └── admin/              ← Admin pages
│
└── (auto-created on first run)
    ├── uploads/            ← Uploaded scan originals
    ├── encrypted/          ← Encrypted scan files
    ├── decrypted/          ← Temporary decrypted files
    ├── models/             ← Trained CNN model files
    └── instance/           ← SQLite database
```

---

## 👥 Role-Based Access Control

| Feature | Admin | Doctor | Radiologist | Receptionist | Patient |
|---------|-------|--------|-------------|--------------|---------|
| Register Patient | ✅ | ❌ | ❌ | ✅ | ❌ |
| View Medical History | ✅ | ✅ | ✅ | ❌ | Own only |
| Upload Scans | ✅ | ✅ | ✅ | ❌ | ❌ |
| View Encrypted Scans | ✅ | ✅ | ✅ | ❌ | ❌ |
| Add Prescription | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manage Appointments | ✅ | View | ❌ | ✅ | ❌ |
| Check-in Patient | ✅ | ❌ | ❌ | ✅ | ❌ |
| Billing Entry | ✅ | ❌ | ❌ | ✅ | ❌ |
| Manage Users | ✅ | ❌ | ❌ | ❌ | ❌ |
| Audit Logs | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 🧠 Encryption System

### How It Works
1. **Upload** medical scan (PNG/JPG/BMP/TIFF)
2. **Encode** → CNN Encoder compresses image to latent space (28×28×256)
3. **Key Derivation** → SHA-256(Patient ID + DOB + Hospital ID) → Logistic Map seed → Chaotic byte key
4. **XOR Scramble** → Latent space XOR'd with chaotic key
5. **Decode** → CNN Decoder reconstructs from scrambled latent → Encrypted image
6. **Store** → Encrypted image stored; original deleted

### Decryption (Same key, self-inverse XOR)
1. Load encrypted image → Encode → Scrambled latent
2. Re-derive same chaotic key (same patient metadata)
3. XOR subtract → Restored latent → Decode → Original image

### Metrics Evaluated
- **PSNR** — Peak Signal-to-Noise Ratio (lower = better encryption, higher = better decryption)
- **SSIM** — Structural Similarity (near 0 when encrypted, near 1 when decrypted)
- **Entropy** — Shannon entropy (near 8 bits when encrypted = random-like)
- **MSE** — Mean Squared Error

---

## 🤖 Training the CNN Model (Optional)

The system works without training — scans are stored but encryption is skipped until the model is trained.

To train:
```bash
python train_model.py
```

- Uses synthetic medical-like image data (no real images required)
- Takes 10–30 minutes on CPU, ~5 minutes on GPU
- Saves model to `models/autoencoder_encoder.keras` and `models/autoencoder_decoder.keras`

---

## 📅 Appointment Booking (Public Homepage)

The homepage (`/`) has a public appointment booking form:
- **New Patient** — Name, Phone, DOB, Email, Doctor, Date, Reason
- **Existing Patient** — Patient ID, Phone, Doctor, Date, Reason
- Appointments saved to database and visible in the Receptionist/Admin dashboard
- WhatsApp link generated for quick notification to `6374307624`

---

## 🔧 Configuration

Edit `app.py` to change:
- `SECRET_KEY` — Change in production
- `SQLALCHEMY_DATABASE_URI` — Switch to PostgreSQL/MySQL for production
- `MAX_CONTENT_LENGTH` — Max file upload size (default 16MB)
- WhatsApp number in `routes/main.py` → `WHATSAPP_NUMBER`

---

## 📦 Dependencies

Key libraries used:
- **Flask** 3.0 — Web framework
- **Flask-SQLAlchemy** — Database ORM
- **Flask-Login** — Session authentication
- **TensorFlow / Keras** — CNN autoencoder
- **NumPy** — Numerical operations
- **Pillow** — Image processing
- **OpenCV** — Computer vision utilities
- **scikit-image** — Image metrics

---

## 🛡️ Security Notes

- Passwords hashed with Werkzeug's PBKDF2-SHA256
- All actions logged to audit trail
- Role-based access enforced at route level
- Encryption keys never stored — re-derived from patient metadata on every access
- For production: use HTTPS, change SECRET_KEY, use PostgreSQL

---

*MediVault HMS — Built with ❤️ for secure, intelligent healthcare data management*
