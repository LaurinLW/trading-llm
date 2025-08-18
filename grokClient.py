import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
import logging
from xai_sdk import Client
from xai_sdk.chat import user, assistant

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
            self.conversation_history: List[Dict[str, str]] = []
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
            self.conversation_history.append({"role": "user", "content": query})
            chat = self.client.chat.create(model=self.model)

            for message in self.conversation_history:
                if message["role"] == "user":
                    chat.append(user(message["content"]))
                elif message["role"] == "assistant":
                    chat.append(assistant(message["content"]))

            response = chat.sample()
            
            if response and hasattr(response, 'content'):
                response_content = {
                    "role": "assistant",
                    "content": response.content
                }
                self.conversation_history.append(response_content)
                logger.info("Received response from Grok API")
                return response_content
            else:
                logger.warning("No valid response content received from Grok API")
                return None

        except Exception as e:
            logger.error(f"Error sending request to Grok API: {e}")
            return None

    def chat(self):
        print("Grok API CLI: Enter your query (or type 'exit' to quit)")
        while True:
            try:
                query = input("Query: ").strip()
                if query.lower() == 'exit':
                    logger.info("Exiting CLI")
                    print("Goodbye!")
                    break
                if not query:
                    print("Please enter a non-empty query.")
                    continue

                response = self.send_request(query)
                if response:
                    print("\nGrok API Response:")
                    print(f"Grok API Response: {response}")
                else:
                    print("Failed to get a response from the Grok API. Check logs for details.\n")

            except KeyboardInterrupt:
                logger.info("CLI interrupted by user")
                print("\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"CLI error: {e}")
                print(f"An error occurred: {e}. Please try again.\n")

def main():
    load_dotenv()

    api_key = os.getenv("API_KEY")
    
    if not api_key:
        logger.error("XAI_API_KEY environment variable not set")
        raise ValueError("Please set the XAI_API_KEY environment variable")

    # Initialize the Grok API client
    grok_client = GrokAPIClient(api_key=api_key)
    grok_client.chat()

if __name__ == "__main__":
    main()