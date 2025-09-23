from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from alpaca.trading.client import TradingClient
from alpaca.trading.models import PortfolioHistory
from alpaca.trading.requests import GetOptionContractsRequest, MarketOrderRequest, GetPortfolioHistoryRequest
from alpaca.trading.enums import ContractType, AssetStatus, OrderSide, TimeInForce
from server.logger import get_logger

logger = get_logger(__name__)


class TradingDataClient:
    def __init__(self, api_key: str, secret_key: str) -> None:
        self.trading_client: TradingClient = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)
        self.last_account_info: Optional[Dict[str, Any]] = None
        self.last_account_value_1min: Optional[Dict[str, Any]] = None
        self.last_account_value_15min: Optional[Dict[str, Any]] = None
        self.last_account_value_1hour: Optional[Dict[str, Any]] = None
        self.last_account_value_1day: Optional[Dict[str, Any]] = None
        self.last_open_positions: Optional[Dict[str, Any]] = None
        logger.info("TradingClient initialized")

    def get_account_info(self) -> Dict[str, float]:
        if not self.last_account_info or (datetime.now() - self.last_account_info["time"]).total_seconds() / 60 >= 1:
            account = self.trading_client.get_account()
            portfolio_value = float(account.portfolio_value)
            cash = float(account.cash)
            buying_power = float(account.buying_power)
            long_market_value = float(account.long_market_value)
            short_market_value = float(account.short_market_value)
            self.last_account_info = {"accountInfo": {"portfolio_value": portfolio_value, "cash": cash, "buying_power": buying_power, "long_market_value": long_market_value, "short_market_value": short_market_value}, "time": datetime.now()}
        return self.last_account_info["accountInfo"]

    def get_account_value(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not self.last_account_value_1min or (datetime.now() - self.last_account_value_1min["time"]).total_seconds() / 60 >= 1:
            self.last_account_value_1min = {"values": self.get_account_value_for_interval("1Min", "1D"), "time": datetime.now()}

        if not self.last_account_value_15min or (datetime.now() - self.last_account_value_15min["time"]).total_seconds() / 60 >= 15:
            self.last_account_value_15min = {"values": self.get_account_value_for_interval("15Min", "5D"), "time": datetime.now()}
        if not self.last_account_value_1hour or (datetime.now() - self.last_account_value_1hour["time"]).total_seconds() / 60 >= 60:
            self.last_account_value_1hour = {"values": self.get_account_value_for_interval("1H", "5D"), "time": datetime.now()}

        if not self.last_account_value_1day or (datetime.now() - self.last_account_value_1day["time"]).total_seconds() / 86400 >= 1:
            self.last_account_value_1day = {"values": self.get_account_value_for_interval("1D", "30D"), "time": datetime.now()}

        return self.last_account_value_1min["values"][-60:], self.last_account_value_15min["values"][-60:], self.last_account_value_1hour["values"][-60:], self.last_account_value_1day["values"][-60:]

    def get_account_value_for_interval(self, timeframe: str, period: str) -> List[Dict[str, Any]]:
        request = GetPortfolioHistoryRequest(period=period, timeframe=timeframe)
        portfolio_history = self.trading_client.get_portfolio_history(request)
        values: List[Dict[str, Any]] = []
        if isinstance(portfolio_history, PortfolioHistory):
            for i in range(len(portfolio_history.timestamp)):
                timestamp = datetime.fromtimestamp(portfolio_history.timestamp[i]).isoformat()
                equity = portfolio_history.equity[i]
                values.append({"timestamp": timestamp, "equity": equity})
        return values

    def get_open_positions(self) -> List[Dict[str, Any]]:
        if not self.last_open_positions or (datetime.now() - self.last_open_positions["time"]).total_seconds() / 60 >= 1:
            open_positions: List[Dict[str, Any]] = []
            positions = self.trading_client.get_all_positions()
            for position in positions:
                symbol = position.symbol
                qty = float(position.qty)
                market_value = float(position.market_value)
                cost_basis = float(position.cost_basis)
                unrealized_pl = float(position.unrealized_pl)
                open_positions.append({"symbol": symbol, "quantity": qty, "market_value": market_value, "original_cost": cost_basis, "unrealized_profit_loss": unrealized_pl})
            self.last_open_positions = {"openPositions": open_positions, "time": datetime.now()}
        return self.last_open_positions["openPositions"]

    def get_options(self, strike_price_gte: str, strike_price_lte: str, option_type: str, expiration_date_gte: str) -> Any:
        try:
            strike_price_gte = float(strike_price_gte)
            strike_price_lte = float(strike_price_lte)
            if strike_price_gte > strike_price_lte:
                raise ValueError("strike_price_gte must be less than or equal to strike_price_lte")
            option_type = option_type.upper()
            if option_type not in ["CALL", "PUT"]:
                raise ValueError("option_type must be 'CALL' or 'PUT'")
            datetime.fromisoformat(expiration_date_gte)  # validate date format
        except ValueError as e:
            return str(e)
        request = GetOptionContractsRequest(
            underlying_symbols=["TSLA"],
            expiration_date_gte=expiration_date_gte,
            strike_price_gte=str(strike_price_gte),
            strike_price_lte=str(strike_price_lte),
            type=ContractType.CALL if option_type == "CALL" else ContractType.PUT,
            limit=15,
            status=AssetStatus.ACTIVE,
        )
        contracts = self.trading_client.get_option_contracts(request)
        return contracts

    def buy_option(self, symbol: str, quantity: float, stop_price: float, profit_price: float) -> str:
        if not isinstance(symbol, str) or not symbol.strip():
            return "Invalid symbol"
        if not isinstance(quantity, (int, float)) or quantity == 0:
            return "Quantity must be a non-zero number"
        if not isinstance(stop_price, (int, float)) or stop_price <= 0:
            return "stop_price must be a positive number"
        if not isinstance(profit_price, (int, float)) or profit_price <= 0:
            return "profit_price must be a positive number"
        try:
            market_order_data = MarketOrderRequest(symbol=symbol, qty=quantity, side=OrderSide.BUY, time_in_force=TimeInForce.DAY, stop_loss={"stop_price": stop_price}, take_profit={"limit_price": profit_price})

            market_order = self.trading_client.submit_order(market_order_data)
            logger.info(f"Bought option {market_order.id}")
        except Exception as e:
            if "40310000" in str(e):
                return "Order was rejected due to the option not being covered. Try a different option."
            else:
                return str(e)
        return f"Success. Remaining cash: {self.getAccountInfo()['cash']}"

    def sell_option(self, symbol: str, quantity: float) -> str:
        if not isinstance(symbol, str) or not symbol.strip():
            return "Invalid symbol"
        if not isinstance(quantity, (int, float)) or quantity == 0:
            return "Quantity must be a non-zero number"
        try:
            market_order_data = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )

            market_order = self.trading_client.submit_order(market_order_data)
            logger.info(f"Sold option {market_order.id}")
        except Exception as e:
            return str(e)
        return f"Success. New cash: {self.getAccountInfo()['cash']}"
