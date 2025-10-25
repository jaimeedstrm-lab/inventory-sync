# GitHub Actions Setup Guide

## Required GitHub Secrets

Du behöver lägga till följande secrets i ditt GitHub repository:

### Hur man lägger till secrets:
1. Gå till: https://github.com/jaimeedstrm-lab/inventory-sync/settings/secrets/actions
2. Klicka på "New repository secret"
3. Lägg till varje secret nedan

### Secrets som behövs:

#### Shopify Secrets
- **SHOPIFY_ACCESS_TOKEN**: `shpat_e42...` (din Shopify Admin API token)
- **SHOPIFY_SHOP_URL**: `natursortimentet.myshopify.com`

#### Oase Outdoors Secrets
- **OASE_USERNAME**: Ditt Oase Outdoors användarnamn
- **OASE_PASSWORD**: Ditt Oase Outdoors lösenord

#### Order Nordic Secrets
- **ORDER_NORDIC_USERNAME**: `12105`
- **ORDER_NORDIC_PASSWORD**: `Tc0Le`

### Config Files (Optional)
Dessa behövs bara om du vill ha config-filer i GitHub Actions:

- **SUPPLIERS_JSON**: Innehållet från `config/suppliers.json`
- **SHOPIFY_JSON**: Innehållet från `config/shopify.json`
- **EMAIL_JSON**: Innehållet från `config/email.json` (om du har email-notiser)

**OBS:** Config-filerna är redan i din kod, så dessa secrets behövs egentligen inte om filerna finns i repot.

## Verifiera Setup

Efter att du lagt till secrets:

1. Gå till "Actions"-fliken på GitHub
2. Välj "Inventory Sync" workflow
3. Klicka "Run workflow" för att testa manuellt
4. Kolla loggen för att se att allt fungerar

## Automatisk Schema

Workflow körs automatiskt:
- **Varje 6:e timme** (00:00, 06:00, 12:00, 18:00 UTC)
- **Manuellt** via "Run workflow" knappen på GitHub Actions

## Vad händer vid varje körning:

1. Kör synk för **Oase Outdoors** (468 produkter via API)
2. Kör synk för **Order Nordic** (1250 produkter via web scraping)
3. Total tid: ~40-60 minuter (mest för Order Nordic scraping)
