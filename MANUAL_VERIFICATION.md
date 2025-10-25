# Manual Verification Guide - Order Nordic Integration

## Syfte
Verifiera att Order Nordic-integrationen fungerar korrekt innan den körs automatiskt i produktion.

---

## ✅ Steg 1: Verifiera Shopify Taggning

### Test:
Gå till Shopify Admin och öppna några slumpmässiga produkter.

### Kontrollera:
1. **Produkter från Order Nordic** ska ha taggen: `supplier:order_nordic`
2. **Produkter från Oase** ska ha taggen: `supplier:oase_outdoors`
3. **Inga produkter** ska ha BÅDA taggarna

### Exempel produkter att kolla:
- American Tourister Bon Air (Order Nordic)
- Easy Camp Adventure (Oase)

**Status:** ☐ OK / ☐ PROBLEM

---

## ✅ Steg 2: Testa Order Nordic Manuellt

### Test:
1. Gå till https://order.se
2. Logga in med: **12105** / **Tc0Le**
3. Sök på EAN: **5414847462863**
4. Kontrollera produktsidan

### Förväntat resultat:
- Produkt: **Kabinväska Bon Air Spinner Svart**
- SKU/Art.nr: **85A09001**
- Lagerstatus: Visas (t.ex. "I lager X st" eller "Åter i lager...")

**Status:** ☐ OK / ☐ PROBLEM

---

## ✅ Steg 3: Kör Automatiskt Test

### Kommando:
```bash
cd "/Users/jaimeedstrom/inventory-sync copy 2"
python3 test_full_integration.py
```

### Förväntat resultat:
```
✅ ALL TESTS PASSED - System ready for production!
```

**Resultat:**
```
Passed: _____ / 10 tester
Failed: _____ / 10 tester
```

**Status:** ☐ OK / ☐ PROBLEM

---

## ✅ Steg 4: Testa Dry-Run med 5 Produkter

### Test:
Kör en liten dry-run för att se hur systemet fungerar:

```bash
cd "/Users/jaimeedstrom/inventory-sync copy 2"
python3 test_mini_sync.py
```

Detta script kommer att:
1. Hämta 5 produkter från Shopify (Order Nordic)
2. Söka efter dem på Order Nordic
3. Visa vad som skulle uppdateras (UTAN att uppdatera)

### Kontrollera:
- **Produkter hittades:** Antal _____
- **Produkter ej hittade:** Antal _____
- **Lager matchningar ser rimliga ut:** ☐ JA / ☐ NEJ

**Status:** ☐ OK / ☐ PROBLEM

---

## ✅ Steg 5: Manuell Jämförelse

### Test:
1. Välj en produkt från Shopify (med Order Nordic tag)
2. Notera dess EAN: _____________________
3. Notera Shopify lager: _____________________
4. Sök manuellt på Order Nordic
5. Notera Order Nordic lager: _____________________

### Kontrollera:
**Ska lagret uppdateras?**
- Om Order Nordic säger "I lager 15 st" → Shopify ska bli 15
- Om Order Nordic säger "Åter i lager..." → Shopify ska bli 0
- Om Order Nordic säger "I lager 0 st" → Shopify ska bli 0

**Status:** ☐ KORREKT / ☐ INKORREKT

---

## ✅ Steg 6: Test med Riktigt Dry-Run (valfritt)

**OBS: Detta kan ta 30-60 minuter beroende på antal produkter!**

### Kommando:
```bash
cd "/Users/jaimeedstrom/inventory-sync copy 2"
python3 main.py --supplier order_nordic --dry-run
```

### Vad händer:
- Systemet söker ALLA Order Nordic-produkter (1250 st)
- Visar vad som SKULLE uppdateras
- Uppdaterar INGENTING (dry-run mode)

### Kontrollera log-filen efteråt:
```bash
ls -lh logs/
cat logs/sync_*.json
```

**Status:** ☐ KÖRDE / ☐ SKIPPADE

---

## ✅ Steg 7: Första Riktiga Körningen

**OBS: Detta uppdaterar FAKTISKT Shopify!**

### Innan du kör:
- ☐ Alla ovanstående tester har gått igenom
- ☐ Dry-run såg bra ut
- ☐ Du är redo att uppdatera lagernivåer

### Kommando:
```bash
cd "/Users/jaimeedstrom/inventory-sync copy 2"
python3 main.py --supplier order_nordic
```

### Efter körning:
1. Gå till Shopify Admin
2. Kolla några slumpmässiga Order Nordic-produkter
3. Verifiera att lagernivåerna är korrekta

**Status:** ☐ KÖRDE / ☐ VÄNTAR

---

## 📋 Sammanfattning

| Test | Status |
|------|--------|
| 1. Shopify taggning | ☐ |
| 2. Manuell Order Nordic | ☐ |
| 3. Automatiskt test | ☐ |
| 4. Mini dry-run | ☐ |
| 5. Manuell jämförelse | ☐ |
| 6. Full dry-run | ☐ |
| 7. Första riktiga körning | ☐ |

---

## ❌ Om något går fel

### Problem: "Authentication failed"
**Lösning:** Kontrollera användarnamn/lösenord i `config/suppliers.json`

### Problem: "Product not found" för produkter som finns
**Lösning:**
1. Kolla att produkten verkligen finns på Order Nordic
2. Sök manuellt för att se om EAN är korrekt

### Problem: "No products tagged with 'supplier:order_nordic'"
**Lösning:** Gå till Shopify och tagga produkterna korrekt

### Problem: Lagernivåer blir felaktiga
**Lösning:**
1. Kör med `--dry-run` först
2. Kolla loggfilen för att se vad som händer
3. Verifiera manuellt några produkter

---

## 🎯 När allt ser bra ut

Systemet är klart för automatisk schemaläggning!

Nästa steg:
1. Pusha till GitHub
2. Sätt upp GitHub Actions för automatisk körning
3. Övervaka första körningarna

