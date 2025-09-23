import json
from typing import Optional, Dict, Any, TypedDict, List
from xai_sdk import Client
from xai_sdk.chat import system, user, tool, tool_result
from server.tradingClient import TradingDataClient
from server.logger import get_logger

logger = get_logger(__name__)


class ChatResponse(TypedDict):
    role: str
    content: str


def getTools():
    return [
        tool(
            name="get_options",
            description="Retrieve available stock options based on strike price range, option type, and expiration date filters.",
            parameters={
                "type": "object",
                "properties": {
                    "strike_price_gte": {"type": "string", "description": "The strike price that should be filtered (greater then equal)."},
                    "strike_price_lte": {"type": "string", "description": "The strike price that should be filtered (less then equal)."},
                    "option_type": {"type": "string", "description": "If it should be a PUT or CALL (only PUT or CALL are valid)"},
                    "expiration_date_gte": {"type": "string", "description": "The value which the expiration date should start e.g. 2025-09-01."},
                },
                "required": ["strike_price_gte", "strike_price_lte", "option_type", "expiration_date_gte"],
            },
        ),
        tool(
            name="buy_option",
            description="Buy a option on the stock market.",
            parameters={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "The option symbol you want to buy."},
                    "quantity": {"type": "number", "description": "The quantity you want to buy."},
                    "stop_price": {"type": "number", "description": "The stop loss price you want to set."},
                    "profit_price": {"type": "number", "description": "The profit take price you want to set."},
                },
                "required": ["symbol", "quantity", "stop_price", "profit_price"],
            },
        ),
        tool(
            name="close_option",
            description="Closes (liquidates) the accounts open position for the given symbol. Works for both long and short positions.",
            parameters={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "The option symbol you want to sell."},
                    "quantity": {"type": "number", "description": "The quantity you want to sell."},
                },
                "required": ["symbol", "quantity"],
            },
        ),
        tool(
            name="get_account_info",
            description="Get all information about your account (cash etc.).",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


class GrokAPIClient:
    def __init__(self, api_key: str, trading_client: TradingDataClient, disable: bool, model: str = "grok-4-fast-reasoning") -> None:
        try:
            self.client: Client = Client(api_key=api_key)
            self.model: str = model
            self.trading_client: TradingDataClient = trading_client
            self.disable: bool = disable
            logger.info(f"Grok API client initialized with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize Grok API client: {e}")
            raise

    def get_settings(self) -> Dict[str, Any]:
        return {"model": self.model, "disabled_grok": self.disable}

    def send_request(self, query: str, interval: int) -> Optional[Dict[str, Any]]:
        if self.disable:
            return
        try:
            logger.info(f"Sending query to Grok API")
            chat = self.client.chat.create(model=self.model, tools=getTools())

            chat.append(
                system(
                    f"You are a professional day trader. You will receive stock data information of TSLA now. Each data point is of a {interval} minute interval. You need to buy/sell options when you feel like it is the correct time. You can only buy and / or sell every {interval} minutes. Make tool calls to buy or sell options. You can use positive or negative quantity when you buy options. If you encounter errors while executing tools, analyze them and take them into consideration. If you want to buy the same option in mass, buy it directly and do not make 10x tool-calls to get 10 options every time. These are your account values {self.trading_client.get_account_info()}. These are your open positions {self.trading_client.get_open_positions()}. Analyze it and tell me your decision in 5 words maximum."
                )
            )
            chat.append(user(query))
            response = chat.sample()

            while response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    if tool_name == "get_options":
                        result = self.trading_client.get_options(tool_args["strike_price_gte"], tool_args["strike_price_lte"], tool_args["option_type"], tool_args["expiration_date_gte"])
                    elif tool_name == "buy_option":
                        result = self.trading_client.buy_option(tool_args["symbol"], tool_args["quantity"], tool_args["stop_price"], tool_args["profit_price"])
                    elif tool_name == "close_option":
                        result = self.trading_client.sell_option(tool_args["symbol"], tool_args["quantity"])
                    elif tool_name == "get_account_info":
                        result = self.trading_client.get_account_info()
                    else:
                        result = f"Unknown tool: {tool_name}"
                    tool_result_msg = tool_result(str(result))
                    chat.append(tool_result_msg)

                response = chat.sample()

            if response and hasattr(response, "content"):
                response_content = {"role": "assistant", "content": response.content}
                logger.info("Received response from Grok API")
                return response_content
            else:
                logger.warning("No valid response content received from Grok API")
                return None

        except Exception as e:
            logger.error(f"Error sending request to Grok API: {e}")
            return None

    def get_signal(self, stock_data: str, interval: int) -> Optional[Dict[str, Any]]:
        response = self.send_request(str(stockData), interval)
        return response
