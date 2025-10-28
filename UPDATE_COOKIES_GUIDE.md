# Guide: Uppdatera Petcare Cookies

## När behöver cookies uppdateras?

Petcare cookies är session-baserade och behöver uppdateras när:
- GitHub Actions sync misslyckas med autentiseringsfel
- Du ser "reCAPTCHA detected" eller "Login failed" i GitHub Actions logs
- Vanligtvis varannan till var tredje månad

## Snabbguide: Uppdatera cookies

### Metod 1: Automatiskt script (rekommenderat)

1. **Kör refresh-scriptet:**
   ```bash
   cd /Users/jaimeedstrom/inventory-sync-current
   python3 refresh_petcare_cookies.py
   ```

2. **Följ instruktionerna:**
   - Webbläsare öppnas automatiskt
   - Lösa reCAPTCHA om den dyker upp
   - Tryck ENTER när du är inloggad
   - Cookiesna sparas till `cookies/petcare_cookies.json`

3. **Kopiera till clipboard:**
   ```bash
   cat cookies/petcare_cookies.json | pbcopy
   ```

4. **Uppdatera GitHub Secret:**
   - Gå till: https://github.com/jaimeedstrm-lab/inventory-sync/settings/secrets/actions
   - Klicka på "PETCARE_COOKIES" → "Update"
   - Klistra in (Cmd+V) det nya innehållet
   - Klicka "Update secret"

**Total tid: ~2 minuter**

### Metod 2: Kombinerat script med automatisk GitHub upload

Kör detta för att både uppdatera och ladda upp till GitHub automatiskt:
```bash
cd /Users/jaimeedstrom/inventory-sync-current
./update_petcare_cookies_to_github.sh
```

(Se nedan för att sätta upp detta script)

### Metod 3: Manuellt via webbläsare

1. Logga in på https://www.petcare.se/mitt-konto/ i Chrome
2. Öppna Developer Tools (Cmd+Option+I)
3. Gå till Application → Cookies → www.petcare.se
4. Kopiera alla cookies manuellt
5. Formatera som JSON
6. Uppdatera GitHub Secret

**⚠️ Inte rekommenderat - mer tidskrävande**

## Tips för att slippa glömma

### 1. Sätt påminnelse i kalender
Lägg till en återkommande påminnelse varannan månad:
- Titel: "Uppdatera Petcare cookies"
- Återkommer: Var 2:a månad
- Anteckning: `cd ~/inventory-sync-current && python3 refresh_petcare_cookies.py`

### 2. Övervaka GitHub Actions
Om en sync misslyckas med autentiseringsfel = dags att uppdatera cookies

### 3. Automatisk notifikation
Ställ in GitHub Actions att skicka email när sync misslyckas:
- Settings → Notifications → Actions
- Aktivera "Send notifications for failed workflows"

## Felsökning

### "Authentication failed" i GitHub Actions
**Orsak:** Cookies har gått ut
**Lösning:** Kör `refresh_petcare_cookies.py` och uppdatera GitHub Secret

### "reCAPTCHA detected" när du kör scriptet
**Orsak:** Petcare kräver manuell reCAPTCHA-lösning
**Lösning:** Detta är normalt - lösa reCAPTCHA i webbläsaren som öppnas

### Scriptet säger "Login appears successful" men cookies funkar inte
**Orsak:** Möjligen inte riktigt inloggad
**Lösning:**
1. Kolla att du ser "Mitt konto"-sidan i webbläsaren
2. Navigera till en produktsida för att verifiera
3. Kör scriptet igen

## Teknisk bakgrund

**Varför behövs cookies?**
- Petcare använder reCAPTCHA v2 vid inloggning
- reCAPTCHA kan inte lösas i headless-läge (GitHub Actions)
- Genom att spara cookies från en manuell inloggning kan GitHub Actions återanvända sessionen

**Hur länge är cookies giltiga?**
- Session cookies: Gäller tills webbläsarsessionen stängs (men Petcare håller dem längre)
- Praktiskt: 2-3 månader i GitHub Actions
- `wordpress_logged_in_*` cookie är den kritiska

**Är det säkert?**
- Cookies innehåller sessionsdata, inte lösenord
- Förvaras säkert i GitHub Secrets (krypterade)
- Endast tillgängliga för GitHub Actions i ditt repo
- Kan när som helst invalideras genom att logga ut från Petcare

## Framtida förbättringar

Möjliga lösningar för att helt automatisera:

1. **Cookie auto-refresh service**
   - Lokal tjänst som kör varje månad
   - Förnyar cookies automatiskt
   - Laddar upp till GitHub

2. **2Captcha / Anti-Captcha integration**
   - Betaltjänst som löser reCAPTCHA programmatiskt
   - Kostar ~$3 per 1000 captchas
   - Kan integreras i GitHub Actions

3. **Petcare API kontakt**
   - Fråga Petcare om de har API-access
   - Eliminerar behovet av web scraping helt

4. **Webhook notifikation**
   - GitHub Actions kan skicka webhook när cookies går ut
   - Du får automatisk notis när uppdatering behövs
