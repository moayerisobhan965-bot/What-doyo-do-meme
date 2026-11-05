# 📧 E-Mail System - Wie bei GitHub/Google

## 🎯 WICHTIG: Standard-Verfahren wie GitHub/Google!

### ✅ SO WIE GITHUB/GOOGLE:

1. ✅ Backend sendet Code per E-Mail
2. ✅ Benutzer erhält Code in E-Mail
3. ✅ Benutzer gibt Code im Frontend ein
4. ✅ Backend verifiziert Code
5. ✅ Account wird aktiviert

---

## 📧 ALLE E-MAIL-TYPEN

1. ✅ **Registrierungs-E-Mail** - Mit Verifizierungs-Code
2. ✅ **Passwort-Reset-E-Mail** - Mit Reset-Code

---

## 🔐 CODE SYSTEM

### 1. Registrierung:

```
1. Benutzer registriert sich
   ↓
2. Backend generiert Code: "456789"
   ↓
3. Backend sendet E-Mail mit Code
   ↓
4. Benutzer erhält E-Mail: "Dein Code: 456789"
   ↓
5. Benutzer gibt Code im Frontend ein
   ↓
6. Backend verifiziert Code
   ↓
7. Account wird aktiviert
```

### 2. Passwort-Reset:

```
1. Benutzer klickt "Passwort vergessen"
   ↓
2. Backend generiert Code: "789123"
   ↓
3. Backend sendet E-Mail mit Code
   ↓
4. Benutzer erhält E-Mail: "Dein Code: 789123"
   ↓
5. Benutzer gibt Code im Frontend ein
   ↓
6. Backend verifiziert Code
   ↓
7. Passwort wird geändert
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
SMTP_FROM_NAME=What Meme
```

### Schritt 3: Docker Compose starten

```bash
docker compose restart
```

---

## 🧪 TESTEN - Wie bei GitHub/Google!

### Test 1: Registrierung mit Code

```bash
# 1. Registrierung ausführen
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "deine@email.de",
    "username": "testuser",
    "password": "password123"
  }'

# 📧 E-Mail wird automatisch gesendet!
# 📧 Code: 456789

# 2. Benutzer erhält E-Mail:
#    "Dein Verifizierungs-Code: 456789"
#    "So verifizierst du deine E-Mail: Kopiere Code, gehe zum Frontend, füge Code ein"

# 3. Benutzer gibt Code ein (im Frontend):
#    Code-Eingabefeld: [456789]
#    [Bestätigen] klicken

# 4. Backend verifiziert Code:
#    ✅ E-Mail erfolgreich verifiziert!

# 5. Jetzt kann sich Benutzer einloggen
```

### Test 2: Passwort-Reset mit Code

```bash
# 1. Passwort vergessen
curl -X POST http://localhost:8000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "deine@email.de"
  }'

# 📧 E-Mail wird automatisch gesendet!
# 📧 Code: 789123

# 2. Benutzer erhält E-Mail:
#    "Dein Reset-Code: 789123"
#    "So setzt du dein Passwort zurück: Kopiere Code, gehe zum Frontend, füge ein"

# 3. Benutzer gibt Code ein (im Frontend):
#    Code-Eingabefeld: [789123]
#    Neues Passwort: [neues-passwort]
#    [Passwort zurücksetzen] klicken

# 4. Backend verifiziert Code:
#    ✅ Passwort erfolgreich geändert!

# 5. Jetzt kann sich Benutzer mit neuem Passwort einloggen
```

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
    verification_code = str(random.randint(100000, 999999))
    # Ergebnis: "456789"

    # 3. CODE IN DATABASE SPEICHERN
    verification = EmailVerification(
        token=verification_code,
        user_id=new_user.id,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(verification)
    await db.commit()

    # 4. 📧 E-Mail MIT CODE SENDEN
    await email_service.send_verification_email(
        to_email=new_user.email,
        username=new_user.username,
        verification_code=verification_code
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
        raise HTTPException(status_code=400, detail="Code ungültig")

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

### 1. **Verifizierungs-Code (6-stellig)**

**Format:** `456789`

**Verwendung:**
- Registrierung
- Bestätigung der E-Mail

**Gültigkeit:** 24 Stunden

**Speicherort:** `email_verifications` Tabelle

### 2. **Reset-Code (6-stellig)**

**Format:** `789123`

**Verwendung:**
- Passwort zurücksetzen
- Passwort vergessen

**Gültigkeit:** 24 Stunden

**Speicherort:** `password_resets` Tabelle

---

## 🎨 IM FRONTEND (BEI BENUTZER)

### Registrierung:

```
┌─────────────────────────────────────┐
│  Registrierung                       │
├─────────────────────────────────────┤
│  E-Mail: deine@email.de             │
│  Username: testuser                 │
│  Passwort: ********                 │
│                                     │
│  [Registrieren]                     │
└─────────────────────────────────────┘

↓ Klick auf Registrieren

┌─────────────────────────────────────┐
│  📧 Code gesendet!                   │
├─────────────────────────────────────┤
│  Eine E-Mail wurde an deine@email.de │
│  gesendet.                          │
│                                     │
│  Dein Code: 456789                  │
│  (Kopiere diesen Code)              │
│                                     │
│  [Code einfügen: _____]             │
│  [Code bestätigen]                  │
└─────────────────────────────────────┘
```

### Passwort-Reset:

```
┌─────────────────────────────────────┐
│  Passwort vergessen                 │
├─────────────────────────────────────┤
│  Gib deine E-Mail ein:              │
│                                     │
│  [deine@email.de] [Senden]          │
└─────────────────────────────────────┘

↓ Klick auf Senden

┌─────────────────────────────────────┐
│  📧 Code gesendet!                   │
├─────────────────────────────────────┤
│  Eine E-Mail wurde an deine@email.de │
│  gesendet.                          │
│                                     │
│  Dein Reset-Code: 789123            │
│                                     │
│  [Neues Passwort: ________________] │
│  [Code: 789123]                     │
│  [Passwort zurücksetzen]            │
└─────────────────────────────────────┘
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

---

## 🎯 ZUSAMMENFASSUNG

### ✅ Backend sendet E-Mails mit Code
### ✅ Benutzer erhält Code in E-Mail
### ✅ Benutzer gibt Code im Frontend ein
### ✅ Backend verifiziert Code
### ✅ Account wird aktiviert

**Das ist das Standard-Verfahren wie bei GitHub/Google!**

---

## 🚀 FERTIG!

Das **Code-System ist voll implementiert** und funktioniert wie bei GitHub/Google!

**Jetzt:**
1. ✅ Resend/Brevo Account erstellen
2. ✅ API Key kopieren
3. ✅ In `.env` eintragen
4. ✅ Container neu starten
5. ✅ Testen!

**Viel Erfolg!** 📧🔐✨
