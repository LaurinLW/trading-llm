import json
from typing import Optional, Dict, Any, TypedDict
import logging
from xai_sdk import Client
from xai_sdk.chat import system, user

# Set up logging for debugging and error tracking
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ChatResponse(TypedDict):
    role: str
    content: str


class GrokAPIClient:
    def __init__(self, api_key: str, model: str = "grok-3-mini"):
        try:
            self.client = Client(api_key=api_key)
            self.model = model
            logger.info(f"Grok API client initialized with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize Grok API client: {e}")
            raise

    def send_request(self, query: str, systemPrompt: str) -> Optional[Dict[str, Any]]:
        try:
            logger.info(f"Sending query to Grok API: {query}")
            chat = self.client.chat.create(model=self.model)

            chat.append(system(systemPrompt))
            chat.append(user(query))
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

    def getSignal(self, stockData, lastBuySignal, lastSellSignal):
        logger.info(str(stockData))
        response = self.send_request(
            str(stockData), f'You are a proffesional day trader. You will recieve stock information of TSLA now. You need to set flags for the trader. The last buy flag was set at {lastBuySignal if lastBuySignal else "never"}. The last sell flag was set at {lastSellSignal if lastSellSignal else "never"}. Analyse it and give an answer in this format: {{"flag": "BUY" | "SELL" | "NONE" }}'
        )
        logger.info(response)
        if response:
            parsed_data = json.loads(response['content'])
            flag = parsed_data["flag"]
            return flag

        return None
