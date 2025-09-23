from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from alpaca.trading.client import TradingClient
from alpaca.trading.models import PortfolioHistory
from alpaca.trading.requests import GetOptionContractsRequest, MarketOrderRequest, GetPortfolioHistoryRequest
from alpaca.trading.enums import ContractType, AssetStatus, OrderSide, TimeInForce
from server.logger import get_logger
from server.models import Cache
from server.utils import ValidationUtils

logger = get_logger(__name__)


class TradingDataClient:
    def __init__(self, api_key: str, secret_key: str) -> None:
        self.trading_client: TradingClient = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)
        self.account_cache = Cache(60)
        self.positions_cache = Cache(60)
        self.account_value_1min_cache = Cache(60)
        self.account_value_15min_cache = Cache(15 * 60)
        self.account_value_1hour_cache = Cache(60 * 60)
        self.account_value_1day_cache = Cache(24 * 60 * 60)
        logger.info("TradingClient initialized")

    def get_account_info(self) -> Dict[str, float]:
        cached = self.account_cache.get()
        if cached:
            return cached
        account = self.trading_client.get_account()
        portfolio_value = float(account.portfolio_value)
        cash = float(account.cash)
        buying_power = float(account.buying_power)
        long_market_value = float(account.long_market_value)
        short_market_value = float(account.short_market_value)
        account_info = {"portfolio_value": portfolio_value, "cash": cash, "buying_power": buying_power, "long_market_value": long_market_value, "short_market_value": short_market_value}
        self.account_cache.set(account_info)
        return account_info

    def get_account_value(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        one = self.account_value_1min_cache.get()
        if not one:
            one = self.get_account_value_for_interval("1Min", "1D")
            self.account_value_1min_cache.set(one)

        fifteen = self.account_value_15min_cache.get()
        if not fifteen:
            fifteen = self.get_account_value_for_interval("15Min", "5D")
            self.account_value_15min_cache.set(fifteen)

        hour = self.account_value_1hour_cache.get()
        if not hour:
            hour = self.get_account_value_for_interval("1H", "5D")
            self.account_value_1hour_cache.set(hour)

        day = self.account_value_1day_cache.get()
        if not day:
            day = self.get_account_value_for_interval("1D", "30D")
            self.account_value_1day_cache.set(day)

        return one[-60:], fifteen[-60:], hour[-60:], day[-60:]

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
        cached = self.positions_cache.get()
        if cached:
            return cached
        open_positions: List[Dict[str, Any]] = []
        positions = self.trading_client.get_all_positions()
        for position in positions:
            symbol = position.symbol
            qty = float(position.qty)
            market_value = float(position.market_value)
            cost_basis = float(position.cost_basis)
            unrealized_pl = float(position.unrealized_pl)
            open_positions.append({"symbol": symbol, "quantity": qty, "market_value": market_value, "original_cost": cost_basis, "unrealized_profit_loss": unrealized_pl})
        self.positions_cache.set(open_positions)
        return open_positions

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
        if error := ValidationUtils.validate_option_params(symbol, quantity, stop_price, profit_price):
            return error
        try:
            market_order_data = MarketOrderRequest(symbol=symbol, qty=quantity, side=OrderSide.BUY, time_in_force=TimeInForce.DAY, stop_loss={"stop_price": stop_price}, take_profit={"limit_price": profit_price})

            market_order = self.trading_client.submit_order(market_order_data)
            logger.info(f"Bought option {market_order.id}")
        except Exception as e:
            if "40310000" in str(e):
                return "Order was rejected due to the option not being covered. Try a different option."
            else:
                return str(e)
        return f"Success. Remaining cash: {self.get_account_info()['cash']}"

    def sell_option(self, symbol: str, quantity: float) -> str:
        if error := ValidationUtils.validate_symbol(symbol):
            return error
        if error := ValidationUtils.validate_quantity(quantity):
            return error
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
        return f"Success. New cash: {self.get_account_info()['cash']}"
