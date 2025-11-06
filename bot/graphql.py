import os
from typing import Any, Dict, List, Optional

import requests


SAI_GRAPHQL_ENDPOINT = os.environ.get("SAI_GRAPHQL_ENDPOINT", "https://sai-keeper.testnet-2.nibiru.fi/query")


class SaiGQLClient:
    def __init__(self, endpoint: Optional[str] = None) -> None:
        self.endpoint = endpoint or SAI_GRAPHQL_ENDPOINT

    def query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = requests.post(
            self.endpoint,
            json={"query": query, "variables": variables or {}},
            timeout=20,
        )
        resp.raise_for_status()
        try:
            payload = resp.json()
        except ValueError as e:
            # If response is not JSON, show what we got
            raise RuntimeError(f"Invalid JSON response from {self.endpoint}: {resp.text[:200]}")
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        return payload.get("data", {})

    def fetch_trades(self, trader: str, is_open: Optional[bool] = None, limit: int = 10, base_symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        query = """
        query Trades($trader: String!, $isOpen: Boolean, $limit: Int!) {
          perp {
            trades(
              where: { trader: $trader, isOpen: $isOpen }
              limit: $limit
              order_by: sequence
              order_desc: true
            ) {
              id
              trader
              isOpen
              isLong
              leverage
              openPrice
              closePrice
              openCollateralAmount
              collateralAmount
              openBlock { block block_ts }
              closeBlock { block block_ts }
              state {
                positionValue
                liquidationPrice
                pnlCollateral
                pnlPct
              }
              perpBorrowing {
                marketId
                baseToken { id name symbol }
                quoteToken { id name symbol }
              }
            }
          }
        }
        """
        data = self.query(query, {"trader": trader, "isOpen": is_open, "limit": limit})
        trades = data.get("perp", {}).get("trades", [])
        
        # Filter by base symbol if provided
        if base_symbol:
            base_symbol_upper = base_symbol.upper()
            trades = [
                t for t in trades
                if (t.get("perpBorrowing", {}).get("baseToken", {}).get("symbol", "") or "").upper() == base_symbol_upper
            ]
        
        return trades

    def fetch_prices(self, limit: int = 100) -> List[Dict[str, Any]]:
        query = """
        query Prices($limit: Int!) {
          oracle {
            tokenPricesUsd(limit: $limit, order_by: token_id) {
              priceUsd
              token { id name symbol }
              lastUpdatedBlock { block block_ts }
            }
          }
        }
        """
        data = self.query(query, {"limit": limit})
        return data.get("oracle", {}).get("tokenPricesUsd", [])
    
    def fetch_price_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch price for a specific token symbol."""
        prices = self.fetch_prices(limit=200)
        symbol_upper = symbol.upper()
        for price in prices:
            token = price.get("token") or {}
            if (token.get("symbol") or "").upper() == symbol_upper:
                return price
        return None
    


