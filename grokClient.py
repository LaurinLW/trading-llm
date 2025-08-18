import os
from dotenv import load_dotenv
import requests
import json
from typing import Optional, Dict, Any
import logging
from xai_sdk import Client
from xai_sdk.chat import user, system

# Set up logging for debugging and error tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GrokAPIClient:
    def __init__(self, api_key: str, model: str = "grok-3-mini"):
        """
        Initialize the Grok API client using the xai_sdk.
        
        Args:
            api_key (str): The xAI API key.
            model (str): The Grok model to use (default: grok-3-mini).
        """
        try:
            self.client = Client(api_key=api_key)
            self.model = model
            logger.info(f"Grok API client initialized with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize Grok API client: {e}")
            raise

    def send_request(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Send a query to the Grok API and return the response.
        
        Args:
            query (str): The query to send to Grok.
        
        Returns:
            Optional[Dict[str, Any]]: The parsed response as a dictionary, or None if the request fails.
        """
        try:
            logger.info(f"Sending query to Grok API: {query}")
            chat = self.client.chat.create(model=self.model)
            chat.append(user(query))
            response = chat.sample()
            
            if response and hasattr(response, 'content'):
                response_content = {
                    "role": "assistant",
                    "content": response.content
                }
                logger.info("Received response from Grok API")
                return response_content
            else:
                logger.warning("No valid response content received from Grok API")
                return None

        except Exception as e:
            logger.error(f"Error sending request to Grok API: {e}")
            return None

def main():
    load_dotenv()

    api_key = os.getenv("API_KEY")
    
    if not api_key:
        logger.error("XAI_API_KEY environment variable not set")
        raise ValueError("Please set the XAI_API_KEY environment variable")

    # Initialize the Grok API client
    grok_client = GrokAPIClient(api_key=api_key)
    
    # Test query to verify connection
    test_query = "Hello, Grok! Can you confirm the API connection?"
    response = grok_client.send_request(test_query)
    
    if response:
        logger.info(f"Grok API Response: {response}")
    else:
        logger.error("Failed to get a response from the Grok API")
        print("Failed to get a response from the Grok API")

if __name__ == "__main__":
    main()