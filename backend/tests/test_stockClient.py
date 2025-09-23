import pytest
from server.stockClient import StockDataClient
from server.models import FinancialDataPoint
from server.data_processor import DataProcessor
from datetime import datetime

@pytest.fixture
def stock_client_setup(mocker):
    mock_stock_client = mocker.patch('server.stockClient.StockHistoricalDataClient')

    mock_stock_client_instance = mocker.MagicMock()
    mock_send_func = mocker.MagicMock()
    mock_grok_client = mocker.MagicMock()

    mock_stock_client.return_value = mock_stock_client_instance

    api_key = "test_api_key"
    secret_key = "test_secret_key"
    interval = 5

    client = StockDataClient(
        api_key=api_key,
        secret_key=secret_key,
        send_func=mock_send_func,
        grok_client=mock_grok_client,
        interval=interval
    )
    client.processor = DataProcessor()
    return {'client': client}

def test_calculateMovingAverage(stock_client_setup):
    client = stock_client_setup['client']

    mockData = [
        FinancialDataPoint(close=300, high=300, low=300, open=300, timestamp=datetime.now(), tradeCount=1, volume=100),
        FinancialDataPoint(close=350, high=350, low=350, open=350, timestamp=datetime.now(), tradeCount=1, volume=100),
        FinancialDataPoint(close=350, high=350, low=350, open=350, timestamp=datetime.now(), tradeCount=1, volume=100),
        FinancialDataPoint(close=400, high=400, low=400, open=400, timestamp=datetime.now(), tradeCount=1, volume=100),
        FinancialDataPoint(close=370, high=370, low=370, open=370, timestamp=datetime.now(), tradeCount=1, volume=100),
    ]

    result = client.processor.calculate_moving_average(mockData, 3)
    assert int(result) == 373

def test_calculateRelativeStrengthIndex(stock_client_setup):
    client = stock_client_setup['client']

    mockData = [
        FinancialDataPoint(close=300, high=300, low=300, open=300, timestamp=datetime.now(), tradeCount=1, volume=100),
        FinancialDataPoint(close=350, high=350, low=350, open=350, timestamp=datetime.now(), tradeCount=1, volume=100),
        FinancialDataPoint(close=350, high=350, low=350, open=350, timestamp=datetime.now(), tradeCount=1, volume=100),
        FinancialDataPoint(close=400, high=400, low=400, open=400, timestamp=datetime.now(), tradeCount=1, volume=100),
        FinancialDataPoint(close=370, high=370, low=370, open=370, timestamp=datetime.now(), tradeCount=1, volume=100),
    ]

    result = client.processor.calculate_relative_strength_index(mockData, 4)
    assert int(result) == 62

def test_invalid_interval(mocker):
    mock_stock_client = mocker.patch('server.stockClient.StockHistoricalDataClient')
    mock_send_func = mocker.MagicMock()
    mock_grok_client = mocker.MagicMock()

    with pytest.raises(ValueError, match="interval must be a positive integer"):
        StockDataClient(
            api_key="test",
            secret_key="test",
            send_func=mock_send_func,
            grok_client=mock_grok_client,
            interval=0
        )
