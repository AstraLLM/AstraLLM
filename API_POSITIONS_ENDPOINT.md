# API Endpoint: `/api/bot/positions`

**Versione:** 1.0.0
**Data Creazione:** 2025-10-23
**Tipo:** GET
**Autenticazione:** Non richiesta

---

## 📋 Descrizione

Endpoint dedicato per recuperare tutte le posizioni attualmente aperte con dati real-time aggiornati dall'exchange.

Questo endpoint **NON modifica** gli endpoint esistenti e fornisce:
- Lista completa delle posizioni aperte
- Calcolo real-time di PnL non realizzato
- Esposizione totale e margine utilizzato
- Tempo di holding per ogni posizione
- Livelli di stop loss, take profit e liquidazione

---

## 🔗 URL

```
GET https://asterbot.avavoice.trade/api/bot/positions
```

---

## 📤 Response Format

### Success Response (200 OK)

```json
{
  "timestamp": "2025-10-23T16:50:15.123456",
  "totalPositions": 2,
  "totalUnrealizedPnL": -1.36,
  "totalExposure": 2345.67,
  "positions": [
    {
      "symbol": "BTCUSDT",
      "side": "LONG",
      "entryPrice": 109372.5,
      "currentPrice": 109897.79,
      "quantity": 0.011,
      "leverage": 20,
      "unrealizedPnL": -5.78,
      "unrealizedPnLPercentage": -0.48,
      "stopLoss": 111013.09,
      "takeProfit": 107731.91,
      "liquidationPrice": 173214.57,
      "strategy": "Breakout Scalping",
      "entryTime": "2025-10-23T15:30:00.000000",
      "holdTimeHours": 1.33,
      "exposure": 1202.97,
      "margin": 60.15
    },
    {
      "symbol": "ETHUSDT",
      "side": "SHORT",
      "entryPrice": 3862.38,
      "currentPrice": 3877.15,
      "quantity": 0.299,
      "leverage": 20,
      "unrealizedPnL": 4.42,
      "unrealizedPnLPercentage": 1.14,
      "stopLoss": 3804.45,
      "takeProfit": 3920.32,
      "liquidationPrice": 1524.36,
      "strategy": "Momentum Reversal",
      "entryTime": "2025-10-23T14:15:30.000000",
      "holdTimeHours": 2.58,
      "exposure": 1158.65,
      "margin": 57.93
    }
  ]
}
```

### Error Response (503 Service Unavailable)

```json
{
  "detail": "Bot not initialized"
}
```

### Error Response (500 Internal Server Error)

```json
{
  "error": "Error message",
  "timestamp": "2025-10-23T16:50:15.123456"
}
```

---

## 📊 Response Fields

### Root Level

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `timestamp` | string (ISO 8601) | Timestamp della richiesta |
| `totalPositions` | integer | Numero totale di posizioni aperte |
| `totalUnrealizedPnL` | float | Somma di tutti i PnL non realizzati (USD) |
| `totalExposure` | float | Esposizione totale (valore nozionale di tutte le posizioni) |
| `positions` | array | Lista delle posizioni aperte (vedi sotto) |

### Position Object

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `symbol` | string | Simbolo della coppia (es. "BTCUSDT") |
| `side` | string | Direzione: "LONG" o "SHORT" |
| `entryPrice` | float | Prezzo di ingresso |
| `currentPrice` | float | Prezzo corrente (real-time da exchange) |
| `quantity` | float | Quantità della posizione |
| `leverage` | integer | Leva finanziaria utilizzata |
| `unrealizedPnL` | float | Profitto/perdita non realizzato (USD) |
| `unrealizedPnLPercentage` | float | PnL non realizzato (%) |
| `stopLoss` | float \| null | Livello di stop loss (null se non impostato) |
| `takeProfit` | float \| null | Livello di take profit (null se non impostato) |
| `liquidationPrice` | float \| null | Prezzo di liquidazione |
| `strategy` | string | Nome della strategia che ha aperto la posizione |
| `entryTime` | string (ISO 8601) | Timestamp di apertura posizione |
| `holdTimeHours` | float | Tempo di holding (ore con 2 decimali) |
| `exposure` | float | Valore nozionale (currentPrice × quantity) |
| `margin` | float | Margine richiesto (exposure / leverage) |

---

## 🧪 Test con PowerShell

### Test Base

```powershell
# Chiamata semplice
$positions = Invoke-RestMethod -Uri "https://asterbot.avavoice.trade/api/bot/positions" -Method Get
$positions | ConvertTo-Json -Depth 10
```

### Test con Analisi

```powershell
# Test completo con analisi
$positions = Invoke-RestMethod -Uri "https://asterbot.avavoice.trade/api/bot/positions"

Write-Host "`n========== OPEN POSITIONS ==========`n" -ForegroundColor Cyan

Write-Host "Total Positions: $($positions.totalPositions)" -ForegroundColor White
Write-Host "Total Unrealized PnL: `$$($positions.totalUnrealizedPnL)" -ForegroundColor $(if ($positions.totalUnrealizedPnL -gt 0) { "Green" } else { "Red" })
Write-Host "Total Exposure: `$$($positions.totalExposure)" -ForegroundColor White

Write-Host "`n--- Position Details ---`n" -ForegroundColor Yellow

foreach ($pos in $positions.positions) {
    Write-Host "[$($pos.symbol)] $($pos.side)" -ForegroundColor Cyan
    Write-Host "  Entry: `$$($pos.entryPrice) → Current: `$$($pos.currentPrice)" -ForegroundColor White
    Write-Host "  Unrealized PnL: `$$($pos.unrealizedPnL) ($($pos.unrealizedPnLPercentage)%)" -ForegroundColor $(if ($pos.unrealizedPnL -gt 0) { "Green" } else { "Red" })
    Write-Host "  Strategy: $($pos.strategy)" -ForegroundColor Gray
    Write-Host "  Hold Time: $($pos.holdTimeHours)h" -ForegroundColor Gray
    Write-Host "  Leverage: $($pos.leverage)x | Margin: `$$($pos.margin)" -ForegroundColor Gray

    if ($pos.stopLoss) {
        Write-Host "  Stop Loss: `$$($pos.stopLoss)" -ForegroundColor Yellow
    }
    if ($pos.takeProfit) {
        Write-Host "  Take Profit: `$$($pos.takeProfit)" -ForegroundColor Green
    }
    if ($pos.liquidationPrice) {
        Write-Host "  Liquidation: `$$($pos.liquidationPrice)" -ForegroundColor Red
    }

    Write-Host ""
}
```

### Test Monitoring Continuo

```powershell
# Monitora posizioni ogni 30 secondi
function Monitor-Positions {
    param([int]$Seconds = 30)

    while ($true) {
        $timestamp = Get-Date -Format "HH:mm:ss"

        try {
            $positions = Invoke-RestMethod -Uri "https://asterbot.avavoice.trade/api/bot/positions"

            Write-Host "[$timestamp] Positions: $($positions.totalPositions) | " -NoNewline -ForegroundColor Cyan
            Write-Host "PnL: `$$($positions.totalUnrealizedPnL) | " -NoNewline -ForegroundColor $(if ($positions.totalUnrealizedPnL -gt 0) { "Green" } else { "Red" })
            Write-Host "Exposure: `$$($positions.totalExposure)" -ForegroundColor White

            # Mostra dettaglio per posizione
            foreach ($pos in $positions.positions) {
                $pnlColor = if ($pos.unrealizedPnL -gt 0) { "Green" } else { "Red" }
                Write-Host "  $($pos.symbol) $($pos.side): `$$($pos.unrealizedPnL) ($($pos.unrealizedPnLPercentage)%)" -ForegroundColor $pnlColor
            }

        } catch {
            Write-Host "[$timestamp] Error: $($_.Exception.Message)" -ForegroundColor Red
        }

        Write-Host ""
        Start-Sleep -Seconds $Seconds
    }
}

# Avvia monitoring (Ctrl+C per fermare)
Monitor-Positions -Seconds 30
```

### Test Export JSON

```powershell
# Salva snapshot posizioni
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$positions = Invoke-RestMethod -Uri "https://asterbot.avavoice.trade/api/bot/positions"
$positions | ConvertTo-Json -Depth 10 | Out-File "positions_snapshot_$timestamp.json"
Write-Host "Snapshot saved: positions_snapshot_$timestamp.json" -ForegroundColor Green
```

---

## 📈 Use Cases

### 1. Dashboard Real-Time
Visualizza posizioni correnti con aggiornamento automatico ogni 30 secondi.

### 2. Risk Management
Monitora esposizione totale e margine utilizzato per evitare sovraesposizione.

### 3. Performance Tracking
Traccia PnL non realizzato per decisioni di chiusura posizioni.

### 4. Alert System
Crea alert quando unrealizedPnL supera soglie predefinite.

### 5. Position Analytics
Analizza tempo di holding medio e correlazione con performance.

---

## 🔄 Relazione con Altri Endpoint

### Differenze vs `/dashboard/summary`

| Caratteristica | `/api/bot/positions` | `/dashboard/summary` |
|----------------|---------------------|----------------------|
| **Focus** | Solo posizioni aperte | Overview completo |
| **Dati** | Real-time da exchange | Dati aggregati + storici |
| **PnL** | Unrealized PnL live | Total PnL + daily PnL |
| **Trade History** | No | Sì (recent trades) |
| **Performance** | No | Sì (strategy performance) |
| **Update Frequency** | Real-time | Cached / periodic |

**Quando usare `/api/bot/positions`:**
- Monitoraggio real-time delle posizioni
- Calcolo PnL non realizzato aggiornato
- Controllo esposizione attuale
- Dashboard dedicata alle posizioni

**Quando usare `/dashboard/summary`:**
- Overview completo del bot
- Analisi performance strategie
- Storico trade recenti
- Statistiche aggregate

---

## 🛠️ Implementazione

### File Modificato
- [api/main.py](api/main.py) - Linee 1190-1296

### Dipendenze
- `bot_instance.risk_manager.positions` - Dict di posizioni aperte
- `bot_instance.client.get_current_price()` - Prezzo real-time da exchange

### Calcoli Effettuati

1. **Unrealized PnL:**
   ```python
   if side == "LONG":
       pnl = (current_price - entry_price) * quantity
   else:  # SHORT
       pnl = (entry_price - current_price) * quantity
   ```

2. **Unrealized PnL %:**
   ```python
   pnl_percentage = (pnl_per_unit / entry_price) * 100
   ```

3. **Exposure:**
   ```python
   exposure = current_price * quantity
   ```

4. **Margin:**
   ```python
   margin = exposure / leverage
   ```

5. **Hold Time:**
   ```python
   hold_time_hours = (now - entry_time).total_seconds() / 3600
   ```

---

## 🚀 Deploy Instructions

### Dopo aver aggiunto l'endpoint:

```bash
# Sul server
docker-compose restart

# Verifica che sia disponibile
curl -s https://asterbot.avavoice.trade/api/bot/positions | jq '.'
```

### Verifica Funzionamento:

```bash
# Deve ritornare JSON valido
curl -s https://asterbot.avavoice.trade/api/bot/positions | jq '.totalPositions'

# Output atteso: numero (es. 2)
```

---

## ⚠️ Note Importanti

1. **Real-Time Data:** I prezzi sono aggiornati ad ogni chiamata API (non cached)
2. **Performance:** Chiamate frequenti comportano più richieste all'exchange
3. **Rate Limiting:** Rispetta i rate limit dell'exchange per `get_current_price()`
4. **Error Handling:** Gestisce errori per singole posizioni senza fallire l'intero endpoint
5. **Null Values:** Stop loss, take profit e liquidation price possono essere null

---

## 📝 Changelog

### Version 1.0.0 (2025-10-23)
- ✅ Endpoint iniziale creato
- ✅ Calcolo real-time PnL non realizzato
- ✅ Supporto per LONG e SHORT positions
- ✅ Calcolo exposure e margin
- ✅ Hold time tracking
- ✅ Error handling robusto

---

## 🎯 Future Enhancements

Possibili miglioramenti futuri:

1. **Caching:** Cache prezzi per 5-10 secondi per ridurre chiamate exchange
2. **Filtering:** Parametri query per filtrare per symbol o strategy
3. **Sorting:** Ordinamento per PnL, exposure, hold time
4. **WebSocket:** Streaming real-time invece di polling
5. **Alerts:** Endpoint separato per configurare alert su posizioni

---

**Creato da:** Claude (Anthropic AI)
**Data:** 2025-10-23
**Status:** ✅ Pronto per deploy
