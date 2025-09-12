import json
from typing import Optional, Dict, Any, TypedDict
import logging
from xai_sdk import Client
from xai_sdk.chat import system, user, tool, tool_result
from server.tadingClient import TradingDataClient

# Set up logging for debugging and error tracking
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


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
                        "exporation_date_gte": {"type": "string", "description": "The value which the experation date should start e.g. 2025-09-01."},
                    },
                    "required": ["strike_price_gte", "strike_price_lte", "option_type", "exporation_date_gte"],
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
                    "properties": {
                    },
                    "required": [],
                },
            ),
        ]

class GrokAPIClient:
    def __init__(self, api_key: str, tradingClient: TradingDataClient, model: str = "grok-3"):
        try:
            self.client = Client(api_key=api_key)
            self.model = model
            self.tradingClient = tradingClient
            logger.info(f"Grok API client initialized with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize Grok API client: {e}")
            raise

    def send_request(self, query: str) -> Optional[Dict[str, Any]]:
        try:
            logger.info(f"Sending query to Grok API")
            chat = self.client.chat.create(model=self.model, tools=getTools())

            chat.append(system(f'You are a proffesional day trader. You will recieve stock information of TSLA now. You need to set flags for the trader and buy/sell options when you feel like it is the correct time. You can use positive or negative quantity when you buy options. If you encounter errors while executing tools, analyse them and take them into consideration. If you want to but the same option on mass buy it directly and do not make 10x tool-calls to get 10 options every time. These are you account values {self.tradingClient.getAccountInfo()}. These are your open positions {self.tradingClient.getOpenPositions()}. Analyse it and give an answer in this format: {{"flag": "BUY" | "SELL" | "NONE" }}. Do not say anything else except this flag json'))
            chat.append(user(query))
            response = chat.sample()

            while response.tool_calls:
                for tool_call in response.tool_calls:
                    print(response.tool_calls)
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    if tool_name == "get_options":
                        result = self.tradingClient.getOptions(tool_args["strike_price_gte"], tool_args["strike_price_lte"], tool_args["option_type"], tool_args["exporation_date_gte"])
                    elif tool_name == "buy_option":
                        result = self.tradingClient.buyOption(tool_args["symbol"], tool_args["quantity"], tool_args["stop_price"], tool_args["profit_price"])
                    elif tool_name == "close_option":
                        result = self.tradingClient.sellOption(tool_args["symbol"], tool_args["quantity"])
                    elif tool_name == "get_account_info":
                        result = self.tradingClient.getAccountInfo()
                    else:
                        result = f"Unknown tool: {tool_name}"
                    logger.info(str(result))
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

    def getSignal(self, stockData):
        logger.info(str(stockData))

        response = self.send_request(str(stockData))
        logger.info(response)
        if response:
            parsed_data = json.loads(response['content'])
            flag = parsed_data["flag"]
            return flag

        return None
