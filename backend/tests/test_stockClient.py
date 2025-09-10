import pytest
from server.stockClient import StockDataClient

@pytest.fixture
def stock_client_setup(mocker):
    mock_stock_client = mocker.patch('server.stockClient.StockHistoricalDataClient')
    mock_run_stream = mocker.patch('server.stockClient.StockDataClient.run_stream')

    mock_stock_client_instance = mocker.MagicMock()
    mock_gateway = mocker.MagicMock()
    mock_grok_client = mocker.MagicMock()

    mock_stock_client.return_value = mock_stock_client_instance

    api_key = "test_api_key"
    secret_key = "test_secret_key"
    mode = "test_mode"

    client = StockDataClient(
        api_key=api_key,
        secret_key=secret_key,
        mode=mode,
        gateway=mock_gateway,
        grokClient=mock_grok_client
    )
    return {'client': client}

def test_calculateMovingAverage(stock_client_setup):
    client = stock_client_setup['client']

    mockData = [{"close": 300}, {"close": 350}, {"close": 350}, {"close": 400}, {"close": 370}]

    result = client.calculateMovingAverage(mockData, 3)
    assert int(result) == 373

def test_calculateRelativeStrengthIndex(stock_client_setup):
    client = stock_client_setup['client']

    mockData = [{"close": 300}, {"close": 350}, {"close": 350}, {"close": 400}, {"close": 370}]

    result = client.calculateRelativeStrengthIndex(mockData, 4)
    assert int(result) == 62
