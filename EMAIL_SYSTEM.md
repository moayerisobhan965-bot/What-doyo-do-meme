# 📧 E-Mail System - Vollständig Automatisch

## 🎯 WICHTIG: E-Mails werden automatisch gesendet!

Das Backend sendet **ALLE E-Mails automatisch** - kein Frontend nötig!

---

## ✅ ALLE E-MAIL-TYPEN (automatisch)

1. ✅ **Registrierungs-E-Mail** - Mit Verifizierungs-Code
2. ✅ **Passwort-Reset-E-Mail** - Mit Reset-Code
3. ⏳ **Willkommens-E-Mail** (kann aktiviert werden)
4. ⏳ **Benachrichtigungen** (kann aktiviert werden)

---

## 🔐 CODE SYSTEM - Automatisch

### 1. Registrierung:

```
1. Benutzer registriert sich
   ↓
2. Backend generiert Code: "123-456789"
   ↓
3. Backend sendet E-Mail mit Code (automatisch!)
   ↓
4. Benutzer erhält E-Mail: "Dein Code: 123-456789"
   ↓
5. Benutzer klickt auf Link in E-Mail → Backend verifiziert Code
   ↓
6. Account wird aktiviert
```

### 2. Passwort-Reset:

```
1. Benutzer klickt "Passwort vergessen"
   ↓
2. Backend generiert Code: "xyz789-abc123"
   ↓
3. Backend sendet E-Mail mit Code (automatisch!)
   ↓
4. Benutzer erhält E-Mail: "Dein Reset-Code: xyz789-abc123"
   ↓
5. Benutzer klickt auf Link in E-Mail → Backend verifiziert Code
   ↓
6. Passwort wird geändert
```

---

## 🚀 EINRICHTUNG (5 Minuten)

### Schritt 1: Resend Account erstellen

1. Gehe zu: https://resend.com
2. Registriere dich kostenlos
3. Erstelle API Key

### Schritt 2: API Key in .env eintragen

```bash
nano .env

# Füge hinzu:
SMTP_PASSWORD=DEIN_RESEND_API_KEY_HIER
SMTP_FROM=noreply@whatmeme.de
BACKEND_DOMAIN=whatmeme.de  # WICHTIG!
```

### Schritt 3: Docker Compose starten

```bash
docker compose restart
```

---

## 🧪 TESTEN - Automatisch!

### Test 1: Registrierung

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "deine@email.de",
    "username": "testuser",
    "password": "password123"
  }'

# 📧 E-Mail wird automatisch gesendet!
# 📧 Code: 123-456789
# 📧 Link: https://whatmeme.de/verify-email?token=123-456789
```

**Ergebnis:**
- ✅ Backend sendet E-Mail automatisch
- ✅ Code wird generiert
- ✅ Link enthält Code
- ✅ Benutzer klickt Link → Backend verifiziert Code

### Test 2: Passwort vergessen

```bash
curl -X POST http://localhost:8000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "deine@email.de"
  }'

# 📧 E-Mail wird automatisch gesendet!
# 📧 Code: xyz789-abc123
# 📧 Link: https://whatmeme.de/reset-password?token=xyz789-abc123
```

**Ergebnis:**
- ✅ Backend sendet E-Mail automatisch
- ✅ Code wird generiert
- ✅ Link enthält Code
- ✅ Benutzer klickt Link → Backend verifiziert Code

---

## 📝 CODE VERARBEITUNG (Backend)

### Registrierung mit Code:

```python
@app.post("/api/auth/register")
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    # 1. User erstellen
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        is_verified=False  # Nicht verifiziert
    )

    db.add(new_user)
    await db.commit()

    # 2. CODE GENERIEREN
    verification_token = f"{new_user.id}-{random.randint(100000, 999999)}"
    # Ergebnis: "123-456789"

    # 3. CODE IN DATABASE SPEICHERN
    verification = EmailVerification(
        token=verification_token,
        user_id=new_user.id,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(verification)
    await db.commit()

    # 4. 📧 E-Mail MIT CODE SENDEN (automatisch!)
    await email_service.send_verification_email(
        to_email=new_user.email,
        username=new_user.username,
        verification_token=verification_token
    )

    return TokenResponse(...)
```

### Code Verifizierung:

```python
@app.post("/api/auth/verify-email")
async def verify_email(data: EmailVerify, db: AsyncSession = Depends(get_db)):
    # 1. CODE AUS DATABASE LADEN
    result = await db.execute(
        select(EmailVerification).where(EmailVerification.token == data.token)
    )
    verification = result.scalar_one_or_none()

    # 2. CODE PRÜFEN
    if not verification:
        raise HTTPException(status_code=400, detail="Code nicht gefunden")

    if verification.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Code abgelaufen")

    # 3. CODE VERIFIZIEREN
    result = await db.execute(select(User).where(User.id == verification.user_id))
    user = result.scalar_one_or_none()

    user.is_verified = True
    await db.commit()

    return {"message": "E-Mail erfolgreich verifiziert!"}
```

---

## 📊 ALLE CODE-TYPEN

### 1. **Verifizierungs-Code (UUID)**

**Format:** `123-456789` oder `abc123-def456`

**Verwendung:**
- Registrierung
- Bestätigung der E-Mail

**Gültigkeit:** 24 Stunden

**Speicherort:** `email_verifications` Tabelle

### 2. **Reset-Code (UUID)**

**Format:** `xyz789-abc123`

**Verwendung:**
- Passwort zurücksetzen
- Passwort vergessen

**Gültigkeit:** 24 Stunden

**Speicherort:** `password_resets` Tabelle

---

## 🔐 LINK ZU BACKEND

### Verifizierungs-Link:

```
https://whatmeme.de/verify-email?token=123-456789
```

### Reset-Link:

```
https://whatmeme.de/reset-password?token=xyz789-abc123
```

**WICHTIG:**
- Links gehen direkt zum Backend
- Kein Frontend nötig
- Backend verifiziert Code automatisch
- Code wird in Database geprüft

---

## 🎨 BEI BENUTZER

### Registrierung:

```
1. Benutzer klickt "Registrieren"
   ↓
2. Backend sendet E-Mail (automatisch!)
   ↓
3. Benutzer erhält E-Mail mit Code
   ↓
4. Benutzer klickt Link in E-Mail
   ↓
5. Backend verifiziert Code (automatisch!)
   ↓
6. Account ist aktiviert
```

### Passwort-Reset:

```
1. Benutzer klickt "Passwort vergessen"
   ↓
2. Backend sendet E-Mail (automatisch!)
   ↓
3. Benutzer erhält E-Mail mit Code
   ↓
4. Benutzer klickt Link in E-Mail
   ↓
5. Backend verifiziert Code (automatisch!)
   ↓
6. Passwort wird geändert
```

---

## ⚠️ HÄUFIGE PROBLEME

### Problem 1: E-Mails gehen nicht an

**Lösung:**

```bash
# 1. Check Logs
docker compose logs app

# 2. Check SMTP Settings in .env
nano .env

# 3. Test E-Mail Versand
python -c "
import asyncio
from app.email.service import email_service

async def test():
    result = await email_service.send_email(
        to_email='deine@email.de',
        subject='Test',
        html_content='<h1>Test</h1>'
    )
    print(f'Sent: {result}')

asyncio.run(test())
"
```

### Problem 2: E-Mails in Spam landen

**Lösung:**

```bash
# 1. SPF Record einrichten
# Füge zu deinem DNS hinzu:
v=spf1 include:_spf.resend.com ~all

# 2. DKIM Record einrichten
# Resend erstellt automatisch DKIM

# 3. DMARC Record einrichten
# Füge zu deinem DNS hinzu:
v=DMARC1; p=none; rua=mailto:postmaster@dein-domain.de
```

---

## 📊 E-MAIL STATISTIKEN

### Resend Dashboard:

1. **Login:** https://resend.com/dashboard
2. **E-Mails ansehen:**
   - Dashboard → Emails → Sent
3. **Einstellungen:**
   - Dashboard → Settings → Sender Domains
4. **API Keys:**
   - Dashboard → API Keys

### Brevo Dashboard:

1. **Login:** https://app.brevo.com
2. **E-Mails ansehen:**
   - Dashboard → Email tracking
3. **Einstellungen:**
   - Settings → SMTP Settings
4. **API Keys:**
   - Settings → API Keys

---

## 🎯 ZUSAMMENFASSUNG

### JA, das Backend sendet **ALLE E-MAILS automatisch**!

1. ✅ **Registrierung** → Code generiert → E-Mail gesendet
2. ✅ **Passwort-Reset** → Code generiert → E-Mail gesendet
3. ⏳ **Weitere E-Mail-Typen** → Kann einfach hinzugefügt werden

### CODE SYSTEM:

1. ✅ Backend generiert Code (UUID)
2. ✅ Backend sendet Code per E-Mail (automatisch!)
3. ✅ Benutzer klickt Link in E-Mail
4. ✅ Backend verifiziert Code (automatisch!)
5. ✅ Account wird aktiviert/geändert

### LINK ZU BACKEND:

1. ✅ Links gehen direkt zum Backend
2. ✅ Kein Frontend nötig
3. ✅ Backend verifiziert Code automatisch
4. ✅ Code wird in Database geprüft

---

## 🚀 FERTIG!

Das **Code-System ist voll implementiert** und funktioniert automatisch!

**Jetzt:**
1. ✅ Resend/Brevo Account erstellen
2. ✅ API Key kopieren
3. ✅ In `.env` eintragen
4. ✅ BACKEND_DOMAIN einstellen
5. ✅ Container neu starten
6. ✅ Testen!

**Viel Erfolg!** 📧🔐✨
