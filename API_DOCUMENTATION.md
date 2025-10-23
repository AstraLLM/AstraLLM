# ASTER Trading Bot - API Documentation for Frontend Team

## Base URL
```
https://asterbot.avavoice.trade
```

## Overview

This API provides real-time trading data from the ASTER trading bot. All endpoints return JSON data and do not require authentication for easy integration.

---

## Endpoints

### 1. Bot Metrics

Get comprehensive bot metrics and trading models performance.

**Endpoint:**
```
GET /api/bot/metrics
```

**Parameters:** None

**Response Format:**
```typescript
{
  timestamp: string;              // ISO 8601 format (e.g., "2025-01-23T10:30:45.123Z")
  globalMetrics: {
    totalVolume: number;          // Total trading volume in USD
    uptime: number;               // Bot uptime percentage (0-100)
    roi: number;                  // Return on Investment percentage
    activeModels: number;         // Number of active trading models
    winRate: number;              // Win rate percentage (0-100)
    totalTrades: number;          // Total number of trades executed
    dailyPnL: number;             // Daily Profit/Loss in USD
    status: "LIVE" | "PAUSED";    // Current bot status
  };
  tradingModels: Array<{
    name: string;                 // Trading model name
    pnl: number;                  // Profit/Loss in USD
    isPositive: boolean;          // true if pnl >= 0
    trades: number;               // Number of trades executed
    winRate: number;              // Win rate percentage (0-100)
    status: "ACTIVE" | "PAUSED";  // Model status
    confidence: number;           // Confidence level (0-100)
    strategies: string[];         // Array of strategy names
    description: string;          // Model description
    performanceData: number[];    // Array of 50 data points for sparkline charts
  }>;
}
```

**Example Request:**
```javascript
const response = await fetch('https://asterbot.avavoice.trade/api/bot/metrics');
const data = await response.json();

console.log(data.globalMetrics.roi);        // 2.34
console.log(data.tradingModels[0].name);    // "Market Making"
console.log(data.tradingModels[0].winRate); // 78.5
```

**Example Response:**
```json
{
  "timestamp": "2025-01-23T10:30:45.123Z",
  "globalMetrics": {
    "totalVolume": 2847.39,
    "uptime": 94.23,
    "roi": 2.34,
    "activeModels": 6,
    "winRate": 67.5,
    "totalTrades": 142,
    "dailyPnL": 45.23,
    "status": "LIVE"
  },
  "tradingModels": [
    {
      "name": "Market Making",
      "pnl": 847.31,
      "isPositive": true,
      "trades": 23,
      "winRate": 78.5,
      "status": "ACTIVE",
      "confidence": 85.2,
      "strategies": ["Market Making"],
      "description": "Trading strategy using Market Making approach",
      "performanceData": [75.2, 77.8, 79.3, 78.1, 82.4, ...]
    },
    {
      "name": "Momentum Reversal",
      "pnl": 1230.45,
      "isPositive": true,
      "trades": 31,
      "winRate": 82.1,
      "status": "ACTIVE",
      "confidence": 88.7,
      "strategies": ["Momentum Reversal"],
      "description": "Trading strategy using Momentum Reversal approach",
      "performanceData": [52.3, 71.5, 85.2, 79.8, 90.1, ...]
    }
  ]
}
```

**Error Response:**
```json
{
  "error": "Bot not initialized",
  "timestamp": "2025-01-23T10:30:45.123Z"
}
```

---

### 2. Chart Performance Data

Get time-series performance data for charting.

**Endpoint:**
```
GET /api/chart/performance
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeframe` | string | `"1m"` | Time interval: `"1m"`, `"5m"`, `"15m"`, `"1h"`, `"4h"`, `"1d"` |
| `points` | number | `150` | Number of data points to return |

**Response Format:**
```typescript
{
  timestamp: string;              // ISO 8601 format
  timeframe: string;              // Requested timeframe
  dataPoints: Array<{
    time: string;                 // Time in "HH:MM" format
    value: number;                // Cumulative PnL value
    timestamp: number;            // Unix timestamp in milliseconds
  }>;
  aiModels: Array<{
    name: string;                 // Model name
    icon: string;                 // Emoji icon
    value: number;                // Current PnL
    subValue: number;             // Previous PnL for comparison
    color: string;                // RGB color string
  }>;
  statistics: {
    min: number;                  // Minimum value in period
    max: number;                  // Maximum value in period
    average: number;              // Average value
    volatility: number;           // Volatility (standard deviation %)
  };
}
```

**Example Request:**
```javascript
// Default request (1m timeframe, 150 points)
const response = await fetch('https://asterbot.avavoice.trade/api/chart/performance');
const data = await response.json();

// Custom timeframe and points
const response2 = await fetch(
  'https://asterbot.avavoice.trade/api/chart/performance?timeframe=1h&points=100'
);
const data2 = await response2.json();
```

**Example Response:**
```json
{
  "timestamp": "2025-01-23T10:30:45.123Z",
  "timeframe": "1m",
  "dataPoints": [
    {
      "time": "05:31",
      "value": 5.23,
      "timestamp": 1706001060000
    },
    {
      "time": "05:32",
      "value": 5.89,
      "timestamp": 1706001120000
    },
    {
      "time": "05:33",
      "value": 6.12,
      "timestamp": 1706001180000
    }
  ],
  "aiModels": [
    {
      "name": "Market Making",
      "icon": "🤖",
      "value": 847.31,
      "subValue": 762.58,
      "color": "rgb(240, 185, 11)"
    },
    {
      "name": "Momentum Reversal",
      "icon": "🧠",
      "value": 1230.45,
      "subValue": 1107.41,
      "color": "rgb(218, 165, 32)"
    },
    {
      "name": "Breakout Scalping",
      "icon": "💎",
      "value": 456.78,
      "subValue": 411.10,
      "color": "rgb(255, 215, 0)"
    }
  ],
  "statistics": {
    "min": 4.85,
    "max": 7.23,
    "average": 5.98,
    "volatility": 2.34
  }
}
```

**Error Response:**
```json
{
  "error": "Bot not initialized",
  "timestamp": "2025-01-23T10:30:45.123Z"
}
```

---

### 3. Dashboard Summary (Legacy)

This is the original dashboard endpoint that provides comprehensive bot data.

**Endpoint:**
```
GET /dashboard/summary
```

**Parameters:** None

**Note:** This endpoint returns more detailed data and is used by the main dashboard. For most use cases, use `/api/bot/metrics` and `/api/chart/performance` instead.

---

## Integration Examples

### React/Next.js Example

```typescript
import { useEffect, useState } from 'react';

const API_BASE = 'https://asterbot.avavoice.trade';

interface BotMetrics {
  timestamp: string;
  globalMetrics: {
    totalVolume: number;
    uptime: number;
    roi: number;
    activeModels: number;
    winRate: number;
    totalTrades: number;
    dailyPnL: number;
    status: 'LIVE' | 'PAUSED';
  };
  tradingModels: Array<{
    name: string;
    pnl: number;
    isPositive: boolean;
    trades: number;
    winRate: number;
    status: 'ACTIVE' | 'PAUSED';
    confidence: number;
    strategies: string[];
    description: string;
    performanceData: number[];
  }>;
}

export default function BotDashboard() {
  const [metrics, setMetrics] = useState<BotMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/bot/metrics`);
        if (!response.ok) throw new Error('Failed to fetch metrics');
        const data = await response.json();
        setMetrics(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();

    // Auto-refresh every 10 seconds
    const interval = setInterval(fetchMetrics, 10000);

    return () => clearInterval(interval);
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!metrics) return <div>No data available</div>;

  return (
    <div>
      <h1>ASTER Trading Bot</h1>
      <div className="metrics">
        <div>ROI: {metrics.globalMetrics.roi}%</div>
        <div>Win Rate: {metrics.globalMetrics.winRate}%</div>
        <div>Total Trades: {metrics.globalMetrics.totalTrades}</div>
        <div>Status: {metrics.globalMetrics.status}</div>
      </div>

      <div className="models">
        {metrics.tradingModels.map((model) => (
          <div key={model.name}>
            <h3>{model.name}</h3>
            <p>PnL: ${model.pnl.toFixed(2)}</p>
            <p>Win Rate: {model.winRate}%</p>
            <p>Trades: {model.trades}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Vanilla JavaScript Example

```javascript
const API_BASE = 'https://asterbot.avavoice.trade';

async function fetchBotMetrics() {
  try {
    const response = await fetch(`${API_BASE}/api/bot/metrics`);
    const data = await response.json();

    // Update UI with metrics
    document.getElementById('roi').textContent = data.globalMetrics.roi + '%';
    document.getElementById('winRate').textContent = data.globalMetrics.winRate + '%';
    document.getElementById('totalTrades').textContent = data.globalMetrics.totalTrades;
    document.getElementById('status').textContent = data.globalMetrics.status;

    // Display trading models
    const modelsContainer = document.getElementById('models');
    modelsContainer.innerHTML = '';

    data.tradingModels.forEach(model => {
      const modelDiv = document.createElement('div');
      modelDiv.className = 'model-card';
      modelDiv.innerHTML = `
        <h3>${model.name}</h3>
        <p>PnL: $${model.pnl.toFixed(2)}</p>
        <p>Win Rate: ${model.winRate}%</p>
        <p>Trades: ${model.trades}</p>
        <p>Status: ${model.status}</p>
      `;
      modelsContainer.appendChild(modelDiv);
    });

  } catch (error) {
    console.error('Error fetching bot metrics:', error);
  }
}

// Fetch on load
fetchBotMetrics();

// Auto-refresh every 10 seconds
setInterval(fetchBotMetrics, 10000);
```

### Chart.js Integration Example

```javascript
import Chart from 'chart.js/auto';

async function createPerformanceChart() {
  const response = await fetch('https://asterbot.avavoice.trade/api/chart/performance?timeframe=1h&points=50');
  const data = await response.json();

  const ctx = document.getElementById('performanceChart').getContext('2d');

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.dataPoints.map(d => d.time),
      datasets: [{
        label: 'Cumulative PnL',
        data: data.dataPoints.map(d => d.value),
        borderColor: 'rgb(240, 185, 11)',
        backgroundColor: 'rgba(240, 185, 11, 0.1)',
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      plugins: {
        title: {
          display: true,
          text: 'Performance Over Time'
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return 'PnL: ' + context.parsed.y.toFixed(2) + '%';
            }
          }
        }
      },
      scales: {
        y: {
          ticks: {
            callback: function(value) {
              return value.toFixed(2) + '%';
            }
          }
        }
      }
    }
  });
}

createPerformanceChart();
```

---

## Real-time Updates

For real-time updates, implement polling with these recommended intervals:

- **Bot Metrics:** Poll every 10 seconds
- **Chart Performance:** Poll every 30-60 seconds (depending on timeframe)

**Example polling implementation:**

```javascript
class BotDataService {
  constructor(baseUrl = 'https://asterbot.avavoice.trade') {
    this.baseUrl = baseUrl;
    this.metricsInterval = null;
    this.chartInterval = null;
  }

  startPolling(onMetricsUpdate, onChartUpdate) {
    // Poll metrics every 10 seconds
    this.metricsInterval = setInterval(async () => {
      const metrics = await this.fetchMetrics();
      onMetricsUpdate(metrics);
    }, 10000);

    // Poll chart data every 30 seconds
    this.chartInterval = setInterval(async () => {
      const chartData = await this.fetchChartData();
      onChartUpdate(chartData);
    }, 30000);

    // Fetch immediately
    this.fetchMetrics().then(onMetricsUpdate);
    this.fetchChartData().then(onChartUpdate);
  }

  stopPolling() {
    if (this.metricsInterval) clearInterval(this.metricsInterval);
    if (this.chartInterval) clearInterval(this.chartInterval);
  }

  async fetchMetrics() {
    const response = await fetch(`${this.baseUrl}/api/bot/metrics`);
    return response.json();
  }

  async fetchChartData(timeframe = '1h', points = 150) {
    const response = await fetch(
      `${this.baseUrl}/api/chart/performance?timeframe=${timeframe}&points=${points}`
    );
    return response.json();
  }
}

// Usage
const botService = new BotDataService();

botService.startPolling(
  (metrics) => {
    console.log('Metrics updated:', metrics);
    // Update your UI here
  },
  (chartData) => {
    console.log('Chart data updated:', chartData);
    // Update your charts here
  }
);

// Don't forget to stop polling when component unmounts
// botService.stopPolling();
```

---

## Error Handling

All endpoints may return an error response if the bot is not initialized or if an error occurs:

```typescript
interface ErrorResponse {
  error: string;
  timestamp: string;
}
```

**Example error handling:**

```javascript
async function fetchWithErrorHandling(url) {
  try {
    const response = await fetch(url);
    const data = await response.json();

    if (data.error) {
      console.error('API Error:', data.error);
      // Show error to user
      return null;
    }

    return data;
  } catch (error) {
    console.error('Network Error:', error);
    // Show network error to user
    return null;
  }
}
```

---

## CORS

All endpoints have CORS enabled with the following configuration:

- **allow_origins:** `["*"]` (all origins allowed)
- **allow_credentials:** `true`
- **allow_methods:** `["*"]` (all HTTP methods)
- **allow_headers:** `["*"]` (all headers)

This means you can call these APIs from any domain without CORS issues.

---

## Rate Limiting

Currently, there is **no rate limiting** on these endpoints. However, please implement reasonable polling intervals (10-30 seconds) to avoid unnecessary load on the server.

**Recommended polling intervals:**
- Bot Metrics: 10 seconds
- Chart Performance: 30-60 seconds

---

## Support & Questions

For questions or issues regarding this API, please contact:

- **Project:** ASTER Trading Bot
- **Environment:** Production
- **Base URL:** https://asterbot.avavoice.trade
- **Version:** 1.0.0

---

## Changelog

### Version 1.1.0 (2025-10-23)
- **NEW:** Added `/api/bot/positions` endpoint for real-time open positions
- Real-time position tracking with live prices
- Unrealized PnL calculations
- Exposure and margin monitoring

### Version 1.0.0 (2025-01-23)
- Initial release
- Added `/api/bot/metrics` endpoint
- Added `/api/chart/performance` endpoint
- Real-time data from live trading bot
- No authentication required

---

## 3. Open Positions (NEW!)

Get all currently open positions with real-time data from the exchange.

**Endpoint:**
```
GET /api/bot/positions
```

**Parameters:** None

**Response Format:**
```typescript
{
  timestamp: string;              // ISO 8601 format
  totalPositions: number;         // Number of open positions
  totalUnrealizedPnL: number;     // Sum of all unrealized PnL (USD)
  totalExposure: number;          // Total notional value of all positions
  positions: Array<{
    symbol: string;               // Trading pair (e.g., "BTCUSDT")
    side: "LONG" | "SHORT";       // Position direction
    entryPrice: number;           // Entry price
    currentPrice: number;         // Current market price (real-time)
    quantity: number;             // Position size
    leverage: number;             // Leverage used
    unrealizedPnL: number;        // Unrealized profit/loss (USD)
    unrealizedPnLPercentage: number; // Unrealized PnL (%)
    stopLoss: number | null;      // Stop loss price (null if not set)
    takeProfit: number | null;    // Take profit price (null if not set)
    liquidationPrice: number | null; // Liquidation price
    strategy: string;             // Strategy that opened the position
    entryTime: string;            // Position entry time (ISO 8601)
    holdTimeHours: number;        // How long position has been open (hours)
    exposure: number;             // Notional value (currentPrice × quantity)
    margin: number;               // Margin required (exposure / leverage)
  }>;
}
```

**Example Response:**
```json
{
  "timestamp": "2025-10-23T16:50:15.123456",
  "totalPositions": 2,
  "totalUnrealizedPnL": -1.36,
  "totalExposure": 2361.62,
  "positions": [
    {
      "symbol": "BTCUSDT",
      "side": "SHORT",
      "entryPrice": 109372.5,
      "currentPrice": 109897.79,
      "quantity": 0.011,
      "leverage": 20,
      "unrealizedPnL": -5.78,
      "unrealizedPnLPercentage": -0.48,
      "stopLoss": 111013.09,
      "takeProfit": 107731.91,
      "liquidationPrice": 173214.57,
      "strategy": "recovered",
      "entryTime": "2025-10-23T15:30:21.000000",
      "holdTimeHours": 1.33,
      "exposure": 1208.88,
      "margin": 60.44
    },
    {
      "symbol": "ETHUSDT",
      "side": "LONG",
      "entryPrice": 3862.38,
      "currentPrice": 3877.15,
      "quantity": 0.299,
      "leverage": 20,
      "unrealizedPnL": 4.42,
      "unrealizedPnLPercentage": 1.14,
      "stopLoss": 3804.45,
      "takeProfit": 3920.32,
      "liquidationPrice": 1524.36,
      "strategy": "recovered",
      "entryTime": "2025-10-23T14:15:30.000000",
      "holdTimeHours": 2.58,
      "exposure": 1159.27,
      "margin": 57.96
    }
  ]
}
```

**Use Cases:**
- Real-time position monitoring dashboard
- Risk management (total exposure tracking)
- PnL tracking before position close
- Alert system for stop loss / take profit levels
- Position analytics (hold time, performance by strategy)

**Update Frequency:** Real-time (prices fetched from exchange on each request)

**Detailed Documentation:** See [API_POSITIONS_ENDPOINT.md](API_POSITIONS_ENDPOINT.md)
