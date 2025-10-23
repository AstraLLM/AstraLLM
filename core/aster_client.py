"""
Aster DEX API Client for Futures and Spot Trading
"""
import time
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from loguru import logger


class AsterFuturesClient:
    """Client for Aster Futures API - Uses Web3 Ethereum signature"""

    def __init__(self, api_key: str, api_secret: str, signer_address: str, user_address: str, private_key: str):
        """
        Initialize Aster Futures Client

        Args:
            api_key: API key from Aster dashboard (not used in this implementation)
            api_secret: API secret from Aster dashboard (not used in this implementation)
            signer_address: Your wallet address that you added as signer on Aster
            user_address: Your main wallet address (same as signer in your case)
            private_key: YOUR wallet private key for signing (the actual key that controls signer_address)
        """
        # Store addresses
        self.user = user_address
        self.signer = signer_address

        # Use YOUR wallet private key for signing (NOT api_secret!)
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        self.private_key = private_key

        self.base_url = "https://fapi.asterdex.com"
        self.session = requests.Session()
        self.w3 = Web3()

        # Cache for symbol precision info
        self.symbol_precision = {}

        logger.info(f"Aster Client initialized:")
        logger.info(f"  User (your wallet): {self.user}")
        logger.info(f"  Signer (agent wallet): {self.signer}")
        logger.info(f"  Signing with private key for address: {Account.from_key(self.private_key).address}")

        # Load exchange info to get precision for all symbols
        self._load_exchange_info()

    def _load_exchange_info(self):
        """Load exchange info and cache symbol precision"""
        try:
            exchange_info = self.get_exchange_info()
            if 'symbols' in exchange_info:
                for symbol_info in exchange_info['symbols']:
                    symbol = symbol_info.get('symbol')
                    if symbol:
                        # Look for LOT_SIZE filter which defines quantity precision
                        for filter_info in symbol_info.get('filters', []):
                            if filter_info.get('filterType') == 'LOT_SIZE':
                                # stepSize tells us the precision (e.g., "0.001" = 3 decimals)
                                step_size = filter_info.get('stepSize', '0.0001')
                                # Count decimals in stepSize
                                if '.' in step_size:
                                    precision = len(step_size.rstrip('0').split('.')[1])
                                else:
                                    precision = 0
                                self.symbol_precision[symbol] = precision
                                break
                logger.info(f"Loaded precision info for {len(self.symbol_precision)} symbols")
        except Exception as e:
            logger.warning(f"Could not load exchange info: {e}. Using default precision.")
            # If we can't load exchange info, set some defaults
            self.symbol_precision = {
                'BTCUSDT': 3,
                'ETHUSDT': 4,
            }

    def _trim_dict(self, d: Dict):
        """Remove None values and convert all values to strings (as per Aster API requirements)"""
        # First, remove None values
        keys_to_remove = [key for key, value in d.items() if value is None]
        for key in keys_to_remove:
            del d[key]

        # Then convert all remaining values to strings
        for key, value in d.items():
            if isinstance(value, (int, float, bool)):
                d[key] = str(value)
            elif isinstance(value, str):
                d[key] = value
            else:
                d[key] = json.dumps(value)

    def _trim_param(self, params: Dict, nonce: int) -> str:
        """Create message to sign from parameters using ABI encoding"""
        # Remove None values
        self._trim_dict(params)

        # Create JSON string with sorted keys, no spaces
        json_str = json.dumps(params, sort_keys=True).replace(' ', '').replace("'", '"')

        logger.debug(f"ABI Encoding params:")
        logger.debug(f"  JSON: {json_str}")
        logger.debug(f"  User: {self.user}")
        logger.debug(f"  Signer: {self.signer}")
        logger.debug(f"  Nonce: {nonce}")

        # ABI encode: [string, address, address, uint256]
        from eth_abi import encode
        encoded = encode(
            ['string', 'address', 'address', 'uint256'],
            [json_str, self.user, self.signer, nonce]
        )

        logger.debug(f"  Encoded bytes length: {len(encoded)}")

        # Calculate Keccak hash
        keccak_hex = self.w3.keccak(encoded).hex()

        return keccak_hex

    def _generate_signature(self, params: Dict, nonce: int) -> str:
        """Generate Web3 signature for authentication"""
        # Get keccak hash of ABI encoded params
        keccak_hex = self._trim_param(params, nonce)
        logger.debug(f"Keccak hash to sign: {keccak_hex}")

        # Sign the hash (it's already a hex string, use hexstr parameter)
        signable_msg = encode_defunct(hexstr=keccak_hex)

        # Sign with private key
        signed_message = Account.sign_message(signable_msg, private_key=self.private_key)

        # Return signature in hex format with 0x prefix (check if already has 0x)
        sig_hex = signed_message.signature.hex()
        if not sig_hex.startswith('0x'):
            sig_hex = '0x' + sig_hex

        logger.debug(f"Generated signature: {sig_hex}")
        return sig_hex

    def _request(self, method: str, endpoint: str, signed: bool = False, **kwargs) -> Dict:
        """Make HTTP request to Aster API"""
        url = f"{self.base_url}{endpoint}"

        headers = {}

        if signed:
            # Get params from kwargs
            params = kwargs.get("params", kwargs.get("json", {}))

            # Generate nonce (timestamp in microseconds)
            nonce = int(time.time() * 1000000)

            # Add timestamp and recvWindow
            params['timestamp'] = int(time.time() * 1000)
            params['recvWindow'] = 50000

            logger.debug(f"Request nonce: {nonce}, timestamp: {params['timestamp']}")

            # Generate signature
            signature = self._generate_signature(params, nonce)

            # Add authentication parameters
            params['nonce'] = nonce
            params['user'] = self.user
            params['signer'] = self.signer
            params['signature'] = signature

            # For POST/DELETE: use form-encoded data
            if method.upper() in ['POST', 'DELETE']:
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
                headers['User-Agent'] = 'PythonApp/1.0'
                kwargs["data"] = params
                if "params" in kwargs:
                    del kwargs["params"]
                if "json" in kwargs:
                    del kwargs["json"]
                logger.debug(f"Request details:")
                logger.debug(f"  Method: {method}")
                logger.debug(f"  URL: {url}")
                logger.debug(f"  Headers: {headers}")
                logger.debug(f"  Data (form-encoded): {kwargs['data']}")
            # For GET: use query parameters
            else:
                kwargs["params"] = params
                if "json" in kwargs:
                    del kwargs["json"]
                if "data" in kwargs:
                    del kwargs["data"]
                logger.debug(f"Request details:")
                logger.debug(f"  Method: {method}")
                logger.debug(f"  URL: {url}")
                logger.debug(f"  Query params: {kwargs['params']}")

        try:
            response = self.session.request(method, url, headers=headers, timeout=10, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Log detailed error information
            error_msg = f"API request failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    error_msg += f" | Response: {error_body}"
                except:
                    error_msg += f" | Response text: {e.response.text[:200]}"
            logger.error(error_msg)
            raise

    # Market Data Endpoints
    def get_exchange_info(self) -> Dict:
        """Get exchange trading rules and symbol information"""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book depth"""
        params = {"symbol": symbol, "limit": limit}
        return self._request("GET", "/fapi/v1/depth", params=params)

    def get_recent_trades(self, symbol: str, limit: int = 500) -> List[Dict]:
        """Get recent trades"""
        params = {"symbol": symbol, "limit": limit}
        return self._request("GET", "/fapi/v1/trades", params=params)

    def get_klines(self, symbol: str, interval: str, limit: int = 500,
                   start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[List]:
        """Get kline/candlestick data"""
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return self._request("GET", "/fapi/v1/klines", params=params)

    def get_ticker_price(self, symbol: Optional[str] = None) -> Dict:
        """Get latest price for a symbol or all symbols"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/ticker/price", params=params)

    def get_ticker_24h(self, symbol: Optional[str] = None) -> Dict:
        """Get 24hr ticker price change statistics"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/ticker/24hr", params=params)

    def get_funding_rate(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get funding rate history"""
        params = {"symbol": symbol, "limit": limit}
        return self._request("GET", "/fapi/v1/fundingRate", params=params)

    # Trading Endpoints
    def create_order(self, symbol: str, side: str, order_type: str,
                     quantity: float, price: Optional[float] = None,
                     leverage: Optional[int] = None,
                     stop_price: Optional[float] = None,
                     time_in_force: str = "GTC",
                     reduce_only: bool = False,
                     close_position: bool = False) -> Dict:
        """Create a new order"""
        # Round quantity based on symbol precision from exchange info
        precision = self.symbol_precision.get(symbol, 4)  # Default to 4 if not found
        quantity = round(quantity, precision)
        logger.debug(f"Rounded quantity for {symbol} to {quantity} ({precision} decimals)")

        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity
        }

        # timeInForce only for LIMIT orders, not for MARKET
        if order_type.upper() != "MARKET":
            params["timeInForce"] = time_in_force

        if price:
            params["price"] = price
        if leverage:
            params["leverage"] = leverage
        if stop_price:
            params["stopPrice"] = stop_price
        if reduce_only:
            params["reduceOnly"] = "true"
        if close_position:
            params["closePosition"] = "true"

        return self._request("POST", "/fapi/v3/order", signed=True, json=params)

    def cancel_order(self, symbol: str, order_id: Optional[str] = None,
                     orig_client_order_id: Optional[str] = None) -> Dict:
        """Cancel an active order"""
        params = {"symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id

        return self._request("DELETE", "/fapi/v3/order", signed=True, json=params)

    def cancel_all_orders(self, symbol: str) -> Dict:
        """Cancel all open orders for a symbol"""
        params = {"symbol": symbol}
        return self._request("DELETE", "/fapi/v3/allOpenOrders", signed=True, json=params)

    def get_order(self, symbol: str, order_id: Optional[str] = None,
                  orig_client_order_id: Optional[str] = None) -> Dict:
        """Check an order's status"""
        params = {"symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id

        return self._request("GET", "/fapi/v3/order", signed=True, params=params)

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open orders"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v3/openOrders", signed=True, params=params)

    # Account Endpoints
    def get_account_info(self) -> Dict:
        """Get current account information"""
        return self._request("GET", "/fapi/v3/account", signed=True)

    def get_balance(self) -> List[Dict]:
        """Get account balance"""
        return self._request("GET", "/fapi/v3/balance", signed=True)

    def get_position_info(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get current position information"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v3/positionRisk", signed=True, params=params)

    def change_leverage(self, symbol: str, leverage: int) -> Dict:
        """Change initial leverage"""
        params = {"symbol": symbol, "leverage": leverage}
        return self._request("POST", "/fapi/v3/leverage", signed=True, json=params)

    def change_margin_type(self, symbol: str, margin_type: str) -> Dict:
        """Change margin type (ISOLATED or CROSSED)"""
        params = {"symbol": symbol, "marginType": margin_type.upper()}
        return self._request("POST", "/fapi/v3/marginType", signed=True, json=params)

    def get_income_history(self, symbol: Optional[str] = None,
                           income_type: Optional[str] = None,
                           limit: int = 100) -> List[Dict]:
        """Get income history"""
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        if income_type:
            params["incomeType"] = income_type
        return self._request("GET", "/fapi/v3/income", signed=True, params=params)

    def get_account_trades(self, symbol: Optional[str] = None,
                          limit: int = 100,
                          start_time: Optional[int] = None,
                          end_time: Optional[int] = None) -> List[Dict]:
        """
        Get account trade history

        Args:
            symbol: Trading pair symbol (optional, if not provided returns all trades)
            limit: Number of trades to return (default 100, max 1000)
            start_time: Timestamp in ms to get trades from (optional)
            end_time: Timestamp in ms to get trades until (optional)

        Returns:
            List of trade records
        """
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return self._request("GET", "/fapi/v3/userTrades", signed=True, params=params)


class AsterSpotClient:
    """Client for Aster Spot API"""

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://sapi.asterdex.com"
        self.session = requests.Session()

    def _generate_signature(self, params: Dict) -> str:
        """Generate HMAC SHA256 signature"""
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _request(self, method: str, endpoint: str, signed: bool = False, **kwargs) -> Any:
        """Make HTTP request to Aster Spot API"""
        url = f"{self.base_url}{endpoint}"
        headers = {"X-API-KEY": self.api_key}

        if signed:
            params = kwargs.get("params", {})
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._generate_signature(params)
            kwargs["params"] = params

        try:
            response = self.session.request(method, url, headers=headers, timeout=10, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Spot API request failed: {e}")
            raise

    # Market Data
    def get_exchange_info(self) -> Dict:
        """Get exchange information"""
        return self._request("GET", "/api/v1/exchangeInfo")

    def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book"""
        params = {"symbol": symbol, "limit": limit}
        return self._request("GET", "/api/v1/depth", params=params)

    def get_recent_trades(self, symbol: str, limit: int = 500) -> List[Dict]:
        """Get recent trades"""
        params = {"symbol": symbol, "limit": limit}
        return self._request("GET", "/api/v1/trades", params=params)

    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> List[List]:
        """Get kline/candlestick data"""
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        return self._request("GET", "/api/v1/klines", params=params)

    def get_ticker_price(self, symbol: Optional[str] = None) -> Any:
        """Get symbol price ticker"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/api/v1/ticker/price", params=params)

    # Trading
    def create_order(self, symbol: str, side: str, order_type: str,
                     quantity: float, price: Optional[float] = None,
                     time_in_force: str = "GTC") -> Dict:
        """Create a new order"""
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity,
            "timeInForce": time_in_force
        }
        if price:
            params["price"] = price

        return self._request("POST", "/api/v1/order", signed=True, params=params)

    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """Cancel an order"""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("DELETE", "/api/v1/order", signed=True, params=params)

    def get_order(self, symbol: str, order_id: str) -> Dict:
        """Get order details"""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/api/v1/order", signed=True, params=params)

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get open orders"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/api/v1/openOrders", signed=True, params=params)

    # Account
    def get_account(self) -> Dict:
        """Get account information"""
        return self._request("GET", "/api/v1/account", signed=True, params={})

    def get_my_trades(self, symbol: str, limit: int = 500) -> List[Dict]:
        """Get account trade history"""
        params = {"symbol": symbol, "limit": limit}
        return self._request("GET", "/api/v1/myTrades", signed=True, params=params)
