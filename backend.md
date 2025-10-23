# SPECIFICHE COMPLETE WEB SERVICES REAL-TIME PER ASTRABOT TRADING DASHBOARD

## PANORAMICA GENERALE

Sistema di backend per fornire dati real-time a una dashboard di trading crypto con AI models. Tutti i dati devono essere reali, nessun mockup. Il sistema deve supportare aggiornamenti in tempo reale tramite WebSocket e fallback HTTP polling.

### REQUISITI TECNICI GENERALI
- Runtime: Node.js 20+ o Bun
- Framework: Next.js 15+ API Routes
- Database: PostgreSQL per storico + Redis per cache real-time
- WebSocket: libreria ws o Socket.io
- Aggiornamenti: 2-5 secondi a seconda del tipo di dato
- Rate limiting: implementare per evitare ban dalle API esterne
- Error handling: retry logic con exponential backoff
- Logging: strutturato con timestamp e livelli (info, warn, error)

---

## 1. API ENDPOINT: BOT METRICS

### Endpoint
\`\`\`
GET /api/bot/metrics
\`\`\`

### Descrizione
Fornisce metriche aggregate del trading bot e performance di tutti i modelli AI attivi.

### Headers Richiesti
\`\`\`
Authorization: Bearer {API_KEY}
Content-Type: application/json
\`\`\`

### Response Schema
\`\`\`typescript
interface BotMetricsResponse {
  timestamp: string; // ISO 8601 format
  globalMetrics: {
    totalVolume: number; // Volume totale in USD
    uptime: number; // Percentuale uptime (0-100)
    roi: number; // Return on Investment percentuale
    activeModels: number; // Numero modelli attivi
    winRate: number; // Percentuale trade vincenti
    totalTrades: number; // Numero totale trade eseguiti
    dailyPnL: number; // Profit/Loss giornaliero in USD
    status: "LIVE" | "PAUSED" | "ERROR";
  };
  tradingModels: Array<{
    name: string; // Nome del modello
    pnl: number; // Profit/Loss in USD
    isPositive: boolean; // true se pnl > 0
    trades: number; // Numero trade eseguiti
    winRate: number; // Percentuale vincite (0-100)
    status: "ACTIVE" | "PAUSED" | "ERROR";
    confidence: number; // Livello confidenza (0-100)
    strategies: string[]; // Array strategie utilizzate
    description: string; // Descrizione modello
    performanceData: number[]; // Array 50 punti per grafico sparkline
  }>;
}
\`\`\`

### Esempio Response
\`\`\`json
{
  "timestamp": "2025-01-23T10:30:45.123Z",
  "globalMetrics": {
    "totalVolume": 2847392.45,
    "uptime": 94.23,
    "roi": 2.03,
    "activeModels": 6,
    "winRate": 17.39,
    "totalTrades": 69,
    "dailyPnL": -2.23,
    "status": "LIVE"
  },
  "tradingModels": [
    {
      "name": "Breakout Scalping",
      "pnl": 847.31,
      "isPositive": true,
      "trades": 23,
      "winRate": 78.5,
      "status": "ACTIVE",
      "confidence": 92.4,
      "strategies": [
        "Support/Resistance Break",
        "Volume Confirmation",
        "Quick Exit"
      ],
      "description": "Captures rapid price movements during breakout events with tight risk management",
      "performanceData": [45.2, 67.8, 89.3, 78.1, 92.4, 88.7, 95.2, 91.3, 87.6, 93.8, 89.2, 94.5, 90.1, 96.3, 92.7, 88.9, 94.2, 91.5, 89.8, 95.7, 93.1, 90.4, 96.8, 94.3, 91.9, 88.5, 95.4, 92.8, 90.2, 97.1, 94.6, 92.3, 89.7, 96.2, 93.5, 91.1, 88.8, 95.9, 93.3, 90.7, 97.4, 94.9, 92.5, 90.1, 96.6, 94.1, 91.7, 89.3, 96.0, 93.7]
    },
    {
      "name": "Momentum Reversal",
      "pnl": 1230.45,
      "isPositive": true,
      "trades": 31,
      "winRate": 82.1,
      "status": "ACTIVE",
      "confidence": 88.7,
      "strategies": [
        "RSI Divergence",
        "MACD Crossover",
        "Trend Exhaustion"
      ],
      "description": "Identifies momentum shifts and reversal points for optimal entry timing",
      "performanceData": [52.3, 71.5, 85.2, 79.8, 90.1, 86.4, 93.7, 89.2, 84.5, 91.8, 87.3, 92.9, 88.6, 94.2, 90.5, 86.7, 92.3, 89.7, 87.9, 93.8, 91.2, 88.4, 95.1, 92.6, 89.8, 86.2, 93.5, 90.9, 88.1, 95.4, 92.8, 90.3, 87.6, 94.7, 91.9, 89.2, 86.9, 94.1, 91.4, 88.7, 95.8, 93.2, 90.6, 88.0, 95.0, 92.4, 89.9, 87.3, 94.4, 91.8]
    },
    {
      "name": "Grid Trading",
      "pnl": -234.12,
      "isPositive": false,
      "trades": 45,
      "winRate": 65.3,
      "status": "ACTIVE",
      "confidence": 76.2,
      "strategies": [
        "Range-bound Trading",
        "Multiple Orders",
        "Profit Accumulation"
      ],
      "description": "Places buy and sell orders at regular intervals to profit from market volatility",
      "performanceData": [48.5, 62.3, 71.8, 68.2, 75.4, 72.1, 79.6, 76.3, 73.8, 80.2, 77.5, 81.9, 78.8, 83.4, 80.7, 77.9, 82.6, 79.8, 77.2, 83.9, 81.3, 78.6, 84.7, 82.1, 79.5, 76.8, 83.2, 80.6, 78.0, 84.9, 82.4, 79.9, 77.3, 84.3, 81.7, 79.2, 76.6, 83.8, 81.2, 78.7, 85.1, 82.6, 80.1, 77.5, 84.5, 82.0, 79.6, 77.0, 84.0, 81.5]
    },
    {
      "name": "Arbitrage Scanner",
      "pnl": 456.78,
      "isPositive": true,
      "trades": 18,
      "winRate": 88.9,
      "status": "ACTIVE",
      "confidence": 95.1,
      "strategies": [
        "Cross-Exchange Arbitrage",
        "Triangular Arbitrage",
        "Statistical Arbitrage"
      ],
      "description": "Exploits price differences across exchanges for risk-free profits",
      "performanceData": [58.7, 76.4, 89.5, 85.3, 94.2, 91.6, 97.8, 95.4, 92.7, 98.3, 96.1, 99.2, 97.5, 99.8, 98.9, 96.3, 99.5, 98.2, 96.8, 99.9, 98.7, 97.4, 100.0, 99.3, 98.1, 95.7, 99.6, 98.4, 97.1, 99.7, 98.9, 97.8, 96.2, 99.4, 98.6, 97.5, 96.0, 99.2, 98.3, 97.2, 99.8, 98.8, 97.9, 96.5, 99.6, 98.7, 97.7, 96.3, 99.5, 98.5]
    },
    {
      "name": "Mean Reversion",
      "pnl": 678.90,
      "isPositive": true,
      "trades": 27,
      "winRate": 74.1,
      "status": "ACTIVE",
      "confidence": 83.6,
      "strategies": [
        "Bollinger Bands",
        "Z-Score Analysis",
        "Statistical Mean"
      ],
      "description": "Capitalizes on price deviations from historical averages",
      "performanceData": [51.2, 68.9, 82.4, 77.6, 87.3, 84.2, 91.5, 88.4, 85.1, 92.3, 89.2, 93.8, 90.7, 95.1, 92.4, 89.6, 94.3, 91.6, 89.0, 95.6, 93.0, 90.3, 96.4, 94.1, 91.7, 88.9, 95.2, 92.8, 90.1, 96.7, 94.5, 92.2, 89.5, 96.1, 93.7, 91.4, 88.7, 95.8, 93.3, 90.9, 97.0, 94.8, 92.6, 90.0, 96.5, 94.2, 91.9, 89.3, 96.3, 93.9]
    },
    {
      "name": "Trend Following",
      "pnl": 1123.45,
      "isPositive": true,
      "trades": 35,
      "winRate": 71.4,
      "status": "ACTIVE",
      "confidence": 81.9,
      "strategies": [
        "Moving Average Crossover",
        "ADX Trend Strength",
        "Breakout Confirmation"
      ],
      "description": "Rides established trends for maximum profit potential",
      "performanceData": [49.8, 66.2, 79.7, 75.4, 84.8, 81.7, 89.2, 86.1, 83.4, 90.1, 87.0, 91.7, 88.6, 93.2, 90.5, 87.7, 92.4, 89.7, 87.1, 93.7, 91.1, 88.4, 94.5, 92.2, 89.8, 87.0, 93.3, 90.9, 88.2, 94.8, 92.6, 90.3, 87.6, 94.2, 91.8, 89.5, 86.8, 93.9, 91.4, 88.9, 95.1, 92.9, 90.7, 88.1, 94.6, 92.3, 90.0, 87.4, 94.1, 91.9]
    }
  ]
}
\`\`\`

### Logica di Calcolo

#### Global Metrics
\`\`\`javascript
// Calcolo uptime
function calculateUptime(startTime, downtimeMinutes) {
  const totalMinutes = (Date.now() - startTime) / 60000;
  return ((totalMinutes - downtimeMinutes) / totalMinutes) * 100;
}

// Calcolo ROI
function calculateROI(totalPnL, initialCapital) {
  return (totalPnL / initialCapital) * 100;
}

// Calcolo Win Rate
function calculateWinRate(trades) {
  const winningTrades = trades.filter(t => t.pnl > 0).length;
  return (winningTrades / trades.length) * 100;
}

// Calcolo Daily PnL
function calculateDailyPnL(trades) {
  const today = new Date().setHours(0, 0, 0, 0);
  const todayTrades = trades.filter(t => new Date(t.timestamp) >= today);
  return todayTrades.reduce((sum, t) => sum + t.pnl, 0);
}
\`\`\`

#### Performance Data (Sparkline)
\`\`\`javascript
// Genera 50 punti per sparkline basati su trade history
function generatePerformanceData(trades, modelName) {
  const modelTrades = trades.filter(t => t.model === modelName);
  const sortedTrades = modelTrades.sort((a, b) => a.timestamp - b.timestamp);
  
  // Raggruppa in 50 bucket temporali
  const buckets = 50;
  const bucketSize = Math.ceil(sortedTrades.length / buckets);
  const performanceData = [];
  
  for (let i = 0; i < buckets; i++) {
    const bucketTrades = sortedTrades.slice(i * bucketSize, (i + 1) * bucketSize);
    const bucketWinRate = calculateWinRate(bucketTrades);
    performanceData.push(parseFloat(bucketWinRate.toFixed(1)));
  }
  
  return performanceData;
}
\`\`\`

### Fonte Dati
- **Aster DEX API**: posizioni aperte, trade history, PnL real-time
- **Database PostgreSQL**: storico trade per calcoli aggregati
- **Redis Cache**: metriche correnti con TTL 3 secondi

### Frequenza Aggiornamento
- **WebSocket**: push ogni 2 secondi
- **HTTP Polling**: fallback ogni 3 secondi

### Error Handling
\`\`\`javascript
// Retry logic con exponential backoff
async function fetchWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
    }
  }
}
\`\`\`

---

## 2. API ENDPOINT: CHART PERFORMANCE DATA

### Endpoint
\`\`\`
GET /api/chart/performance
\`\`\`

### Descrizione
Fornisce dati per il grafico principale che mostra performance aggregate di tutti i modelli AI nel tempo.

### Query Parameters
\`\`\`typescript
interface ChartQueryParams {
  timeframe: "1m" | "5m" | "15m" | "1h" | "4h" | "1d"; // Timeframe candele
  points?: number; // Numero punti dati (default: 150)
}
\`\`\`

### Response Schema
\`\`\`typescript
interface ChartPerformanceResponse {
  timestamp: string; // ISO 8601
  timeframe: string; // Timeframe richiesto
  dataPoints: Array<{
    time: string; // Formato "HH:MM"
    value: number; // Valore aggregato PnL
    timestamp: number; // Unix timestamp milliseconds
  }>;
  aiModels: Array<{
    name: string; // Nome modello AI
    icon: string; // Emoji icon
    value: number; // PnL corrente
    subValue: number; // PnL precedente per confronto
    color: string; // RGB color string
  }>;
  statistics: {
    min: number; // Valore minimo nel periodo
    max: number; // Valore massimo nel periodo
    average: number; // Media valori
    volatility: number; // Deviazione standard percentuale
  };
}
\`\`\`

### Esempio Response
\`\`\`json
{
  "timestamp": "2025-01-23T10:30:45.123Z",
  "timeframe": "1m",
  "dataPoints": [
    { "time": "05:31", "value": 5234.56, "timestamp": 1706001060000 },
    { "time": "05:32", "value": 5289.12, "timestamp": 1706001120000 },
    { "time": "05:33", "value": 5312.45, "timestamp": 1706001180000 },
    { "time": "05:34", "value": 5298.78, "timestamp": 1706001240000 },
    { "time": "05:35", "value": 5345.23, "timestamp": 1706001300000 }
  ],
  "aiModels": [
    {
      "name": "GPT-4o",
      "icon": "🤖",
      "value": 3126.08,
      "subValue": 2897.31,
      "color": "rgb(240, 185, 11)"
    },
    {
      "name": "Claude",
      "icon": "🧠",
      "value": 2431.31,
      "subValue": 2188.72,
      "color": "rgb(218, 165, 32)"
    },
    {
      "name": "Gemini",
      "icon": "💎",
      "value": 988.72,
      "subValue": 888.72,
      "color": "rgb(255, 215, 0)"
    }
  ],
  "statistics": {
    "min": 4850.23,
    "max": 6234.89,
    "average": 5456.78,
    "volatility": 2.34
  }
}
\`\`\`

### Logica di Calcolo

#### Data Points Aggregation
\`\`\`javascript
// Aggrega PnL di tutti i modelli per timeframe
async function aggregateChartData(timeframe, points = 150) {
  const interval = getIntervalMilliseconds(timeframe); // 1m = 60000ms
  const endTime = Date.now();
  const startTime = endTime - (interval * points);
  
  // Query database per tutti i trade nel periodo
  const trades = await db.query(`
    SELECT 
      timestamp,
      SUM(pnl) as total_pnl
    FROM trading_history
    WHERE timestamp >= $1 AND timestamp <= $2
    GROUP BY timestamp
    ORDER BY timestamp ASC
  `, [new Date(startTime), new Date(endTime)]);
  
  // Raggruppa in bucket temporali
  const dataPoints = [];
  let cumulativePnL = 0;
  
  for (let i = 0; i < points; i++) {
    const bucketStart = startTime + (i * interval);
    const bucketEnd = bucketStart + interval;
    
    const bucketTrades = trades.rows.filter(t => 
      t.timestamp >= bucketStart && t.timestamp < bucketEnd
    );
    
    const bucketPnL = bucketTrades.reduce((sum, t) => sum + t.total_pnl, 0);
    cumulativePnL += bucketPnL;
    
    dataPoints.push({
      time: formatTime(bucketStart),
      value: parseFloat(cumulativePnL.toFixed(2)),
      timestamp: bucketStart
    });
  }
  
  return dataPoints;
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

function getIntervalMilliseconds(timeframe) {
  const intervals = {
    "1m": 60000,
    "5m": 300000,
    "15m": 900000,
    "1h": 3600000,
    "4h": 14400000,
    "1d": 86400000
  };
  return intervals[timeframe];
}
\`\`\`

#### AI Models Performance
\`\`\`javascript
// Calcola performance per ogni modello AI
async function calculateAIModelsPerformance() {
  const models = ["GPT-4o", "Claude", "Gemini"];
  const results = [];
  
  for (const model of models) {
    // PnL corrente (ultima ora)
    const currentPnL = await db.query(`
      SELECT SUM(pnl) as total
      FROM trading_history
      WHERE model_name = $1 AND timestamp > NOW() - INTERVAL '1 hour'
    `, [model]);
    
    // PnL precedente (ora precedente)
    const previousPnL = await db.query(`
      SELECT SUM(pnl) as total
      FROM trading_history
      WHERE model_name = $1 
        AND timestamp > NOW() - INTERVAL '2 hours'
        AND timestamp <= NOW() - INTERVAL '1 hour'
    `, [model]);
    
    results.push({
      name: model,
      icon: getModelIcon(model),
      value: parseFloat(currentPnL.rows[0].total || 0),
      subValue: parseFloat(previousPnL.rows[0].total || 0),
      color: getModelColor(model)
    });
  }
  
  return results;
}

function getModelIcon(model) {
  const icons = {
    "GPT-4o": "🤖",
    "Claude": "🧠",
    "Gemini": "💎"
  };
  return icons[model] || "🔮";
}

function getModelColor(model) {
  const colors = {
    "GPT-4o": "rgb(240, 185, 11)",
    "Claude": "rgb(218, 165, 32)",
    "Gemini": "rgb(255, 215, 0)"
  };
  return colors[model] || "rgb(200, 200, 200)";
}
\`\`\`

#### Statistics Calculation
\`\`\`javascript
function calculateStatistics(dataPoints) {
  const values = dataPoints.map(dp => dp.value);
  
  const min = Math.min(...values);
  const max = Math.max(...values);
  const average = values.reduce((sum, v) => sum + v, 0) / values.length;
  
  // Calcola volatilità (deviazione standard)
  const squaredDiffs = values.map(v => Math.pow(v - average, 2));
  const variance = squaredDiffs.reduce((sum, v) => sum + v, 0) / values.length;
  const stdDev = Math.sqrt(variance);
  const volatility = (stdDev / average) * 100;
  
  return {
    min: parseFloat(min.toFixed(2)),
    max: parseFloat(max.toFixed(2)),
    average: parseFloat(average.toFixed(2)),
    volatility: parseFloat(volatility.toFixed(2))
  };
}
\`\`\`

### Sliding Window Implementation
\`\`\`javascript
// Mantieni buffer in Redis per performance
class ChartDataBuffer {
  constructor(redis, maxPoints = 150) {
    this.redis = redis;
    this.maxPoints = maxPoints;
    this.key = 'chart:data:buffer';
  }
  
  async addPoint(point) {
    // Aggiungi nuovo punto
    await this.redis.rpush(this.key, JSON.stringify(point));
    
    // Rimuovi punto più vecchio se supera limite
    const length = await this.redis.llen(this.key);
    if (length > this.maxPoints) {
      await this.redis.lpop(this.key);
    }
  }
  
  async getAll() {
    const data = await this.redis.lrange(this.key, 0, -1);
    return data.map(item => JSON.parse(item));
  }
}
\`\`\`

### Fonte Dati
- **Database PostgreSQL**: trade history aggregato
- **Redis Buffer**: sliding window ultimi 150 punti
- **Aster DEX API**: PnL real-time per modelli AI

### Frequenza Aggiornamento
- **Nuovo punto dati**: ogni 60 secondi (1m timeframe)
- **WebSocket push**: ogni 2 secondi con ultimo punto
- **Full refresh**: ogni 30 secondi

---

## 3. API ENDPOINT: CRYPTO MARKET DATA

### Endpoint
\`\`\`
GET /api/market/crypto
\`\`\`

### Descrizione
Fornisce dati di mercato real-time per le principali criptovalute con indicatori tecnici calcolati.

### Query Parameters
\`\`\`typescript
interface MarketQueryParams {
  symbols?: string; // Comma-separated (default: "BTC,ETH,SOL,BNB")
}
\`\`\`

### Response Schema
\`\`\`typescript
interface CryptoMarketResponse {
  timestamp: string; // ISO 8601
  currentTime: string; // Formato "HH:MM"
  cryptos: Array<{
    symbol: string; // Ticker symbol
    name: string; // Nome completo
    price: number; // Prezzo corrente USD
    priceChange24h: number; // Variazione % 24h
    technicalIndicators: {
      sma: number; // Simple Moving Average (20 periodi)
      ema: number; // Exponential Moving Average (20 periodi)
      rsi: number; // Relative Strength Index (14 periodi)
      macd: number; // MACD line
      macdSignal: number; // MACD signal line
      atr: number; // Average True Range
      ao: number; // Awesome Oscillator
    };
    volume: {
      vol24h: number; // Volume 24h USD
      obv: number; // On Balance Volume
    };
    support: number; // Livello supporto più vicino
    resistance: number; // Livello resistenza più vicino
  }>;
}
\`\`\`

### Esempio Response
\`\`\`json
{
  "timestamp": "2025-01-23T10:30:45.123Z",
  "currentTime": "10:30",
  "cryptos": [
    {
      "symbol": "BTC",
      "name": "Bitcoin",
      "price": 109328.45,
      "priceChange24h": 2.34,
      "technicalIndicators": {
        "sma": 108500.23,
        "ema": 109100.56,
        "rsi": 62.5,
        "macd": 245.3,
        "macdSignal": 198.7,
        "atr": 1250.8,
        "ao": 125.4
      },
      "volume": {
        "vol24h": 28500000000,
        "obv": 15200000000
      },
      "support": 108000,
      "resistance": 112000
    }
  ]
}
\`\`\`

### Logica di Calcolo

#### Fetch Price Data
\`\`\`javascript
// Integrazione con CoinGecko API
async function fetchCryptoPrices(symbols) {
  const symbolsLower = symbols.map(s => s.toLowerCase()).join(',');
  
  const response = await fetch(
    `https://api.coingecko.com/api/v3/simple/price?ids=${symbolsLower}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true`,
    {
      headers: {
        'Accept': 'application/json'
      }
    }
  );
  
  return await response.json();
}

// Integrazione con Binance API per dati più dettagliati
async function fetchBinanceData(symbol) {
  const response = await fetch(
    `https://api.binance.com/api/v3/ticker/24hr?symbol=${symbol}USDT`
  );
  
  return await response.json();
}
\`\`\`

#### Technical Indicators Calculation
\`\`\`javascript
const { SMA, EMA, RSI, MACD, ATR, AO } = require('technicalindicators');

// Fetch historical price data per calcoli
async function fetchHistoricalPrices(symbol, periods = 100) {
  const response = await fetch(
    `https://api.binance.com/api/v3/klines?symbol=${symbol}USDT&interval=1h&limit=${periods}`
  );
  
  const klines = await response.json();
  
  return {
    close: klines.map(k => parseFloat(k[4])),
    high: klines.map(k => parseFloat(k[2])),
    low: klines.map(k => parseFloat(k[3])),
    volume: klines.map(k => parseFloat(k[5]))
  };
}

async function calculateTechnicalIndicators(symbol) {
  const historicalData = await fetchHistoricalPrices(symbol);
  
  // Simple Moving Average (20 periodi)
  const sma = SMA.calculate({
    period: 20,
    values: historicalData.close
  });
  
  // Exponential Moving Average (20 periodi)
  const ema = EMA.calculate({
    period: 20,
    values: historicalData.close
  });
  
  // Relative Strength Index (14 periodi)
  const rsi = RSI.calculate({
    period: 14,
    values: historicalData.close
  });
  
  // MACD (12, 26, 9)
  const macd = MACD.calculate({
    values: historicalData.close,
    fastPeriod: 12,
    slowPeriod: 26,
    signalPeriod: 9,
    SimpleMAOscillator: false,
    SimpleMASignal: false
  });
  
  // Average True Range (14 periodi)
  const atr = ATR.calculate({
    high: historicalData.high,
    low: historicalData.low,
    close: historicalData.close,
    period: 14
  });
  
  // Awesome Oscillator
  const ao = AO.calculate({
    high: historicalData.high,
    low: historicalData.low,
    fastPeriod: 5,
    slowPeriod: 34
  });
  
  // Prendi ultimi valori
  return {
    sma: parseFloat(sma[sma.length - 1].toFixed(2)),
    ema: parseFloat(ema[ema.length - 1].toFixed(2)),
    rsi: parseFloat(rsi[rsi.length - 1].toFixed(1)),
    macd: parseFloat(macd[macd.length - 1].MACD.toFixed(2)),
    macdSignal: parseFloat(macd[macd.length - 1].signal.toFixed(2)),
    atr: parseFloat(atr[atr.length - 1].toFixed(2)),
    ao: parseFloat(ao[ao.length - 1].toFixed(2))
  };
}
\`\`\`

#### Support/Resistance Calculation
\`\`\`javascript
// Calcola livelli supporto/resistenza usando pivot points
function calculateSupportResistance(high, low, close) {
  const pivot = (high + low + close) / 3;
  
  const resistance1 = (2 * pivot) - low;
  const support1 = (2 * pivot) - high;
  
  const resistance2 = pivot + (high - low);
  const support2 = pivot - (high - low);
  
  // Trova livelli più vicini al prezzo corrente
  const resistanceLevels = [resistance1, resistance2].sort((a, b) => a - b);
  const supportLevels = [support1, support2].sort((a, b) => b - a);
  
  const nearestResistance = resistanceLevels.find(r => r > close) || resistanceLevels[0];
  const nearestSupport = supportLevels.find(s => s < close) || supportLevels[0];
  
  return {
    support: parseFloat(nearestSupport.toFixed(2)),
    resistance: parseFloat(nearestResistance.toFixed(2))
  };
}
\`\`\`

#### On Balance Volume (OBV)
\`\`\`javascript
function calculateOBV(prices, volumes) {
  let obv = 0;
  const obvValues = [obv];
  
  for (let i = 1; i < prices.length; i++) {
    if (prices[i] > prices[i - 1]) {
      obv += volumes[i];
    } else if (prices[i] < prices[i - 1]) {
      obv -= volumes[i];
    }
    obvValues.push(obv);
  }
  
  return obvValues[obvValues.length - 1];
}
\`\`\`

### Implementazione Completa
\`\`\`javascript
async function getCryptoMarketData(symbols = ['BTC', 'ETH', 'SOL', 'BNB']) {
  const cryptos = [];
  
  for (const symbol of symbols) {
    try {
      // Fetch dati paralleli
      const [priceData, binanceData, historicalData] = await Promise.all([
        fetchCryptoPrices([symbol]),
        fetchBinanceData(symbol),
        fetchHistoricalPrices(symbol)
      ]);
      
      // Calcola indicatori tecnici
      const indicators = await calculateTechnicalIndicators(symbol);
      
      // Calcola supporto/resistenza
      const { support, resistance } = calculateSupportResistance(
        Math.max(...historicalData.high.slice(-24)),
        Math.min(...historicalData.low.slice(-24)),
        historicalData.close[historicalData.close.length - 1]
      );
      
      // Calcola OBV
      const obv = calculateOBV(historicalData.close, historicalData.volume);
      
      cryptos.push({
        symbol,
        name: getFullName(symbol),
        price: parseFloat(binanceData.lastPrice),
        priceChange24h: parseFloat(binanceData.priceChangePercent),
        technicalIndicators: indicators,
        volume: {
          vol24h: parseFloat(binanceData.quoteVolume),
          obv: parseFloat(obv.toFixed(0))
        },
        support,
        resistance
      });
    } catch (error) {
      console.error(`Error fetching data for ${symbol}:`, error);
    }
  }
  
  return {
    timestamp: new Date().toISOString(),
    currentTime: new Date().toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    }),
    cryptos
  };
}

function getFullName(symbol) {
  const names = {
    'BTC': 'Bitcoin',
    'ETH': 'Ethereum',
    'SOL': 'Solana',
    'BNB': 'BNB'
  };
  return names[symbol] || symbol;
}
\`\`\`

### Caching Strategy
\`\`\`javascript
// Cache in Redis con TTL 3 secondi
async function getCachedMarketData(redis, symbols) {
  const cacheKey = `market:${symbols.join(',')}`;
  
  // Prova cache
  const cached = await redis.get(cacheKey);
  if (cached) {
    return JSON.parse(cached);
  }
  
  // Fetch fresh data
  const data = await getCryptoMarketData(symbols);
  
  // Salva in cache
  await redis.set(cacheKey, JSON.stringify(data), { ex: 3 });
  
  return data;
}
\`\`\`

### Fonte Dati
- **CoinGecko API**: prezzi base e market cap
- **Binance API**: dati trading dettagliati, volumi, klines
- **Calcoli server-side**: tutti gli indicatori tecnici

### Frequenza Aggiornamento
- **HTTP Polling**: ogni 3 secondi
- **WebSocket**: push su variazioni > 0.1%

### Rate Limiting
\`\`\`javascript
// Implementa rate limiter per API esterne
const Bottleneck = require('bottleneck');

const coinGeckoLimiter = new Bottleneck({
  maxConcurrent: 1,
  minTime: 1200 // 50 req/min = 1 req ogni 1.2s
});

const binanceLimiter = new Bottleneck({
  maxConcurrent: 5,
  minTime: 50 // 1200 req/min = 20 req/s
});

// Wrap fetch calls
const fetchCoinGecko = coinGeckoLimiter.wrap(fetch);
const fetchBinance = binanceLimiter.wrap(fetch);
\`\`\`

---

## 4. API ENDPOINT: AI MARKET ANALYSIS

### Endpoint
\`\`\`
GET /api/analysis/ai-market
\`\`\`

### Descrizione
Fornisce analisi di mercato generate da AI con sentiment, segnali di trading e analisi dettagliate per ogni asset.

### Response Schema
\`\`\`typescript
interface AIMarketAnalysisResponse {
  timestamp: string; // ISO 8601
  markets: Array<{
    symbol: string; // Ticker symbol
    name: string; // Nome completo
    price: number; // Prezzo corrente USD
    change24h: number; // Variazione % 24h
    sentiment: "BULLISH" | "BEARISH" | "NEUTRAL";
    aiSignal: "BUY" | "SELL" | "HOLD";
    confidence: number; // Confidenza segnale (0-100)
    analysis: string; // Analisi breve (1-2 frasi)
    detailedAnalysis: string; // Analisi dettagliata (150-200 parole)
    volume24h: string; // Volume formattato (es. "$42.3B")
    marketCap: string; // Market cap formattato
    onChainMetrics: {
      whaleActivity: "HIGH" | "MEDIUM" | "LOW";
      exchangeInflow: number; // Negativo = outflow
      exchangeOutflow: number; // Positivo = accumulation
      activeAddresses: number;
    };
    technicalLevels: {
      support: number[]; // Array 3 livelli supporto
      resistance: number[]; // Array 3 livelli resistenza
    };
  }>;
}
\`\`\`

### Logica di Calcolo

#### AI Signal Generation Algorithm
\`\`\`javascript
// Algoritmo scoring multi-fattore per generare segnali AI
function calculateAISignal(indicators, sentiment, onChain) {
  let score = 0;
  const weights = {
    technical: 0.35,
    sentiment: 0.25,
    onChain: 0.25,
    volume: 0.15
  };
  
  // 1. Technical Score (35%)
  let technicalScore = 0;
  
  // RSI scoring
  if (indicators.rsi < 30) {
    technicalScore += 30; // Oversold = bullish
  } else if (indicators.rsi > 70) {
    technicalScore -= 30; // Overbought = bearish
  } else {
    // Neutral zone: prefer 40-60 range
    technicalScore += (50 - Math.abs(indicators.rsi - 50)) * 0.6;
  }
  
  // MACD scoring
  if (indicators.macd > indicators.macdSignal && indicators.macd > 0) {
    technicalScore += 25; // Bullish crossover
  } else if (indicators.macd < indicators.macdSignal && indicators.macd < 0) {
    technicalScore -= 25; // Bearish crossover
  } else if (indicators.macd > indicators.macdSignal) {
    technicalScore += 15; // Bullish but below zero
  } else {
    technicalScore -= 15; // Bearish but above zero
  }
  
  // Price vs EMA scoring
  const priceVsEma = ((indicators.price - indicators.ema) / indicators.ema) * 100;
  if (priceVsEma > 2) {
    technicalScore += 20; // Strong uptrend
  } else if (priceVsEma < -2) {
    technicalScore -= 20; // Strong downtrend
  } else {
    technicalScore += priceVsEma * 10; // Proportional
  }
  
  // ATR volatility adjustment
  const atrPercent = (indicators.atr / indicators.price) * 100;
  if (atrPercent > 3) {
    technicalScore *= 0.8; // Reduce confidence in high volatility
  }
  
  score += technicalScore * weights.technical;
  
  // 2. Sentiment Score (25%)
  let sentimentScore = 0;
  
  if (sentiment.fearGreedIndex > 70) {
    sentimentScore += 20; // Greed = bullish
  } else if (sentiment.fearGreedIndex < 30) {
    sentimentScore += 15; // Fear = contrarian buy
  } else {
    sentimentScore += (sentiment.fearGreedIndex - 50) * 0.4;
  }
  
  // Social sentiment
  sentimentScore += sentiment.socialScore * 0.3; // -50 to +50
  
  // News sentiment
  sentimentScore += sentiment.newsScore * 0.2; // -50 to +50
  
  score += sentimentScore * weights.sentiment;
  
  // 3. On-Chain Score (25%)
  let onChainScore = 0;
  
  // Exchange flow (outflow = bullish)
  const netFlow = onChain.exchangeOutflow - onChain.exchangeInflow;
  const flowPercent = (netFlow / onChain.totalSupply) * 100;
  onChainScore += flowPercent * 1000; // Scale up
  
  // Whale activity
  if (onChain.whaleActivity === 'HIGH' && netFlow > 0) {
    onChainScore += 30; // Whales accumulating
  } else if (onChain.whaleActivity === 'HIGH' && netFlow < 0) {
    onChainScore -= 30; // Whales distributing
  }
  
  // Active addresses trend
  const addressGrowth = onChain.activeAddressesChange; // Percentage
  onChainScore += addressGrowth * 2;
  
  score += onChainScore * weights.onChain;
  
  // 4. Volume Score (15%)
  let volumeScore = 0;
  
  const volumeRatio = indicators.volume24h / indicators.avgVolume30d;
  if (volumeRatio > 1.5) {
    volumeScore += 30; // High volume = strong move
  } else if (volumeRatio < 0.7) {
    volumeScore -= 20; // Low volume = weak move
  } else {
    volumeScore += (volumeRatio - 1) * 30;
  }
  
  score += volumeScore * weights.volume;
  
  // 5. Determine Signal and Confidence
  let signal, confidence;
  
  if (score > 50) {
    signal = 'BUY';
    confidence = Math.min(95, Math.round(score));
  } else if (score < -50) {
    signal = 'SELL';
    confidence = Math.min(95, Math.round(Math.abs(score)));
  } else {
    signal = 'HOLD';
    confidence = Math.round(70 - Math.abs(score) * 0.4);
  }
  
  return { signal, confidence, score };
}
\`\`\`

---

## 5. WEBSOCKET REAL-TIME UPDATES

### Endpoint
\`\`\`
wss://your-domain.com/ws/trading
\`\`\`

### Descrizione
WebSocket server per push real-time di tutti i dati invece di polling HTTP.

### Message Types

#### Subscribe Request (Client → Server)
\`\`\`json
{
  "type": "subscribe",
  "channels": ["bot-metrics", "chart-data", "market-data", "ai-analysis"],
  "symbols": ["BTC", "ETH", "SOL", "BNB"]
}
\`\`\`

#### Bot Metrics Update (Server → Client)
\`\`\`json
{
  "type": "bot-metrics",
  "timestamp": "2025-01-23T10:30:45.123Z",
  "data": {
    "globalMetrics": {},
    "tradingModels": []
  }
}
\`\`\`

### Server Implementation (Node.js)

\`\`\`javascript
const WebSocket = require('ws');
const wss = new WebSocket.Server({ port: 8080 });

const clients = new Map();

wss.on('connection', (ws, req) => {
  const clientId = generateClientId();
  
  clients.set(clientId, {
    ws,
    subscriptions: [],
    symbols: []
  });
  
  ws.on('message', async (message) => {
    const data = JSON.parse(message);
    await handleClientMessage(clientId, data);
  });
  
  ws.on('close', () => {
    clients.delete(clientId);
  });
});

// Background job: Update bot metrics every 2 seconds
setInterval(async () => {
  const metrics = await getBotMetrics();
  
  clients.forEach((client) => {
    if (client.subscriptions.includes('bot-metrics') && 
        client.ws.readyState === WebSocket.OPEN) {
      client.ws.send(JSON.stringify({
        type: 'bot-metrics',
        timestamp: new Date().toISOString(),
        data: metrics
      }));
    }
  });
}, 2000);
\`\`\`

---

## 6. DATABASE SCHEMA (PostgreSQL)

\`\`\`sql
-- Trading history per modelli
CREATE TABLE trading_history (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  model_name VARCHAR(100) NOT NULL,
  symbol VARCHAR(10) NOT NULL,
  side VARCHAR(10) NOT NULL,
  entry_price DECIMAL(18, 8) NOT NULL,
  exit_price DECIMAL(18, 8),
  quantity DECIMAL(18, 8) NOT NULL,
  pnl DECIMAL(18, 2),
  pnl_percent DECIMAL(8, 4),
  status VARCHAR(20) NOT NULL,
  strategy VARCHAR(100),
  confidence DECIMAL(5, 2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Chart data points
CREATE TABLE chart_data (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  timeframe VARCHAR(10) NOT NULL,
  value DECIMAL(18, 2) NOT NULL,
  model_name VARCHAR(100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices per performance
CREATE INDEX idx_trading_history_timestamp ON trading_history(timestamp DESC);
CREATE INDEX idx_trading_history_model ON trading_history(model_name, timestamp DESC);
CREATE INDEX idx_chart_data_timeframe ON chart_data(timeframe, timestamp DESC);
\`\`\`

---

## 7. REDIS CACHE STRUCTURE

\`\`\`
# Bot metrics (TTL: 3s)
bot:metrics:current -> JSON

# Chart data buffer (no TTL, max 150 items)
chart:data:1m -> LIST
chart:data:5m -> LIST

# Market data per symbol (TTL: 3s)
market:BTC:current -> JSON
market:ETH:current -> JSON

# AI analysis per symbol (TTL: 5s)
analysis:BTC:current -> JSON
analysis:ETH:current -> JSON
\`\`\`

---

## 8. DEPLOYMENT ARCHITECTURE

### Infrastructure

\`\`\`
Frontend (Vercel) → API Gateway (Vercel Functions)
                  ↓
        WebSocket Server (Railway)
                  ↓
        Redis Cache (Upstash)
                  ↓
        PostgreSQL (Supabase/Neon)
                  ↓
        External APIs (CoinGecko, Binance, etc.)
\`\`\`

### Hosting Recommendations

- **Frontend**: Vercel ($20/mese)
- **API Backend**: Vercel Serverless Functions ($20/mese)
- **WebSocket Server**: Railway ($7-20/mese)
- **Database**: Supabase/Neon ($25/mese)
- **Cache**: Upstash Redis ($10-20/mese)

**Total Monthly Cost**: $90-150

---

## 9. MONITORING & LOGGING

### Metrics to Track

\`\`\`javascript
const metrics = {
  api_response_time_ms: {},
  external_api_latency_ms: {},
  cache_hit_rate: {},
  websocket_connections: {},
  error_rate: {},
  db_query_time_ms: {}
};
\`\`\`

### Health Check Endpoint

\`\`\`javascript
// GET /api/health
export async function GET() {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    services: {}
  };
  
  // Check database, Redis, external APIs
  // Return health status
  
  return Response.json(health);
}
\`\`\`

---

## 10. SECURITY & RATE LIMITING

### API Authentication

\`\`\`javascript
async function authenticateRequest(req) {
  const apiKey = req.headers.get('authorization')?.replace('Bearer ', '');
  
  if (!apiKey) {
    throw new Error('Missing API key');
  }
  
  // Verify API key in database
  const validKey = await db.query(
    'SELECT * FROM api_keys WHERE key = $1 AND active = true',
    [apiKey]
  );
  
  if (validKey.rows.length === 0) {
    throw new Error('Invalid API key');
  }
  
  return validKey.rows[0];
}
\`\`\`

### Rate Limiting

\`\`\`javascript
const rateLimit = require('express-rate-limit');

const apiLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  message: 'Too many requests'
});

app.use('/api/', apiLimiter);
\`\`\`

---

## 11. ENVIRONMENT VARIABLES

\`\`\`bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/astrabot

# Redis
REDIS_URL=redis://default:password@host:6379
KV_REST_API_URL=https://your-redis.upstash.io
KV_REST_API_TOKEN=your-token

# External APIs
COINGECKO_API_KEY=your-key
BINANCE_API_KEY=your-key
LUNARCRUSH_API_KEY=your-key
OPENAI_API_KEY=sk-your-key

# Aster DEX
ASTER_API_KEY=your-key
ASTER_API_URL=https://api.aster-dex.com/v1

# Application
NODE_ENV=production
API_BASE_URL=https://astrabot.com
WEBSOCKET_URL=wss://ws.astrabot.com
\`\`\`

---

## SUMMARY & NEXT STEPS

### Implementazione Prioritaria

1. **Fase 1 - Core APIs (Settimana 1)**
   - Setup database PostgreSQL + Redis
   - Implementa `/api/bot/metrics`
   - Implementa `/api/chart/performance`
   - Integra con Aster DEX API

2. **Fase 2 - Market Data (Settimana 2)**
   - Implementa `/api/market/crypto`
   - Integra CoinGecko + Binance APIs
   - Calcola indicatori tecnici
   - Setup caching Redis

3. **Fase 3 - AI Analysis (Settimana 3)**
   - Implementa `/api/analysis/ai-market`
   - Integra LunarCrush + Glassnode
   - Setup OpenAI per analisi
   - Implementa AI signal algorithm

4. **Fase 4 - WebSocket (Settimana 4)**
   - Setup WebSocket server
   - Implementa real-time push
   - Client-side integration
   - Testing e ottimizzazione

5. **Fase 5 - Production (Settimana 5)**
   - Deploy su Vercel + Railway
   - Setup monitoring e logging
   - Load testing
   - Security audit

### Checklist Finale

- [ ] Database schema creato e migrato
- [ ] Redis cache configurato
- [ ] Tutte le API implementate e testate
- [ ] WebSocket server funzionante
- [ ] Integrazioni esterne configurate
- [ ] Rate limiting implementato
- [ ] Logging e monitoring attivi
- [ ] Security audit completato
- [ ] Load testing superato
- [ ] Documentation completa
- [ ] Deploy in production
