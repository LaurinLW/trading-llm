import logging
from datetime import datetime
from alpaca.trading.client import TradingClient
from alpaca.trading.models import PortfolioHistory
from alpaca.trading.requests import GetOptionContractsRequest, MarketOrderRequest, GetPortfolioHistoryRequest
from alpaca.trading.enums import ContractType, AssetStatus, OrderSide, TimeInForce

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TradingDataClient:
    def __init__(self, api_key: str, secret_key: str):
        self.trading_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)
        self.lastAccountInfo = None
        self.lastAccountValueOne = None
        self.lastAccountValueFifteen = None
        self.lastAccountValueHour = None
        self.lastAccountValueDay = None
        self.lastOpenPositions = None
        logger.info("TradingClient initialized")

    def getAccountInfo(self):
        if not self.lastAccountInfo or (datetime.now() - self.lastAccountInfo["time"]).total_seconds() / 60 >= 1:
            account = self.trading_client.get_account()
            portfolio_value = float(account.portfolio_value)
            cash = float(account.cash)
            buying_power = float(account.buying_power)
            long_market_value = float(account.long_market_value)
            short_market_value = float(account.short_market_value)
            self.lastAccountInfo = {"accountInfo": {"portfolio_value": portfolio_value, "cash": cash, "buying_power": buying_power, "long_market_value": long_market_value, "short_market_value": short_market_value}, "time": datetime.now()}
        return self.lastAccountInfo["accountInfo"]

    def getAccountValue(self):
        if not self.lastAccountValueOne or (datetime.now() - self.lastAccountValueOne["time"]).total_seconds() / 60 >= 1:
            self.lastAccountValueOne = {"values": self.getAccountValueForInterval("1Min", "1D"), "time": datetime.now()}

        if not self.lastAccountValueFifteen or (datetime.now() - self.lastAccountValueFifteen["time"]).total_seconds() / 60 >= 15:
            self.lastAccountValueFifteen = {"values": self.getAccountValueForInterval("15Min", "5D"), "time": datetime.now()}
        if not self.lastAccountValueHour or (datetime.now() - self.lastAccountValueHour["time"]).total_seconds() / 60 >= 60:
            self.lastAccountValueHour = {"values": self.getAccountValueForInterval("1H", "5D"), "time": datetime.now()}

        if not self.lastAccountValueDay or (datetime.now() - self.lastAccountValueDay["time"]).total_seconds() / 86400 >= 1:
            self.lastAccountValueDay = {"values": self.getAccountValueForInterval("1D", "30D"), "time": datetime.now()}

        return self.lastAccountValueOne["values"][-60:], self.lastAccountValueFifteen["values"][-60:], self.lastAccountValueHour["values"][-60:], self.lastAccountValueDay["values"][-60:]

    def getAccountValueForInterval(self, timeframe, period):
        request = GetPortfolioHistoryRequest(period=period, timeframe=timeframe)
        portfolio_history = self.trading_client.get_portfolio_history(request)
        values = []
        if type(portfolio_history) is PortfolioHistory:
            for i in range(len(portfolio_history.timestamp)):
                timestamp = datetime.fromtimestamp(portfolio_history.timestamp[i]).isoformat()
                equity = portfolio_history.equity[i]
                values.append({"timestamp": timestamp, "equity": equity})
        return values

    def getOpenPositions(self):
        if not self.lastOpenPositions or (datetime.now() - self.lastOpenPositions["time"]).total_seconds() / 60 >= 1:
            openPositions = []
            positions = self.trading_client.get_all_positions()
            for position in positions:
                symbol = position.symbol
                qty = float(position.qty)
                market_value = float(position.market_value)
                cost_basis = float(position.cost_basis)
                unrealized_pl = float(position.unrealized_pl)
                openPositions.append({"symbol": symbol, "quantity": qty, "market_value": market_value, "original_cost": cost_basis, "unrealized_profit_loss": unrealized_pl})
            self.lastOpenPositions = {"openPositions": openPositions, "time": datetime.now()}
        return self.lastOpenPositions["openPositions"]

    def getOptions(self, strike_price_gte, strike_price_lte, option_type, exporation_date_gte):
        request = GetOptionContractsRequest(
            underlying_symbols=["TSLA"],
            expiration_date_gte=exporation_date_gte,
            strike_price_gte=strike_price_gte,
            strike_price_lte=strike_price_lte,
            type=ContractType.CALL if option_type == "CALL" else ContractType.PUT,
            limit=15,
            status=AssetStatus.ACTIVE,
        )
        contracts = self.trading_client.get_option_contracts(request)
        return contracts

    def buyOption(self, symbol, quantity, stop_price, profit_price):
        try:
            market_order_data = MarketOrderRequest(symbol=symbol, qty=quantity, side=OrderSide.BUY, time_in_force=TimeInForce.DAY, stop_loss={"stop_price": stop_price}, take_profit={"limit_price": profit_price})

            market_order = self.trading_client.submit_order(market_order_data)
            logger.info(f"Bought option {market_order.id}")
        except Exception as e:
            if "40310000" in str(e):
                return "Order was rejected due to the option not being covered. Try a different option."
            else:
                return str(e)
        return f"Success. Remaining Cash {self.getAccountInfo()['cash']}"

    def sellOption(self, symbol, quantity):
        try:
            market_order_data = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )

            market_order = self.trading_client.submit_order(market_order_data)
            logger.info(f"Solled option {market_order.id}")
        except Exception as e:
            return str(e)
        return f"Success. New Cash {self.getAccountInfo()['cash']}"
