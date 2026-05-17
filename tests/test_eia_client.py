import pytest
from unittest.mock import patch, MagicMock
from ingestion.eia_client import (
    get_series,
    get_cushing_stocks,
    get_refinery_utilization,
    get_crude_imports,
    get_crude_production,
)

############################################################
#################### build mock response ###################
############################################################

# mocking the EIA API response
# Using real shape to validate the structure expected by the code
mock_response = {
    "response": {
        "total": "1",
        "dateFormat": "YYYY-MM-DD",
        "frequency": "weekly",
        "data": [
            {
                "period": "2026-05-08",
                "duoarea": "YCUOK",
                "area-name": "NA",
                "product": "EPC0",
                "product-name": "Crude Oil",
                "process": "SAX",
                "series": "W_EPC0_SAX_YCUOK_MBBL",
                "value": "27422",
                "units": "MBBL",
            }
        ],
    }
}


def make_mock_response(data: dict) -> MagicMock:
    """Helper that builds a fake requests.Response object. Usually,
    request.get() returns a Response object with methods like .json()
    and .raise_for_status(). This helper builds a MagicMock that
    simulates that behavior, returning the provided data when .json() 
    is called but does not make a real API/HTTP request. raise_for_status() 
    is set to None, simulating a successful API call (200 OK). json() is set
    to return whatever dict passed in as data.

    Args:
        data (dict): The fake response body to return when .json() is called.

    Returns:
        MagicMock: A fake requests.Response object with pre-configured return
                        values for .json() and .raise_for_status().
    """    
    mock = MagicMock() # create a new mock object
    mock.raise_for_status.return_value = None  # no exception raised for status (successful run)
    mock.json.return_value = data  # return the provided data as JSON instead of real API request
    return mock

############################################################
#################### get_series() tests ####################
############################################################

# @patch is a decorator that intercepts request.get inside the eia_client.py
# and replaces it with a fake for the duration of this text. Path must match exactly
# where requests.get is imported in eia_client.py. The mock object is passed as an 
# argument to the test function.
@patch("ingestion.eia_client.requests.get")
def test_get_series_returns_dict(mock_get):
    """Tests that get_series() returns a dict when the API responds
    successfully.

    Args:
        mock_get (MagicMock): A mock object simulating a requests.Response
                                ingested by @patch so no real HTTP request
                                is made.

    Returns:
        None: Pass/fair determined by whether the assert statement raises an
                AssertionError.
    """    
    # set the mock to return our fake response
    mock_get.return_value = make_mock_response(mock_response) 
    # calls the real function, which will hit the fake instead of the real API
    result = get_series("petroleum/sum/sndw")
    # Assert if result is a dict.
    # isinstance() checks the type. If False, test failed.
    assert isinstance(result, dict)  
    
@patch("ingestion.eia_client.requests.get")
def test_get_series_response_has_data_key(mock_get):
    """Tests that the response dict contains the expected nested keys 
    'response' and 'data'. The EIA API should return a JSON  object with 
    a top-level 'response' key containing metadata and  a 'data' key with 
    the time series data. This test catches that before it reaches load.py.

    Args:
        mock_get (MagicMock): A mock object simulating a requests.Response
                                ingested by @patch so no real HTTP request
                                is made.

    Returns:
        None: Pass/fail determined by whether the assert statement raises 
                an AssertionError.
    """    
    
    mock_get.return_value = make_mock_response(mock_response)
    
    result = get_series("petroleum/sum/sndw")
    
    # Assert that the top-level 'response' key is in the result dict
    # then check that 'data' key is inside the 'response' dict. 
    # If either is missing, test fails.
    assert "response" in result and "data" in result["response"]
    
    
@patch("ingestion.eia_client.requests.get")
def test_get_series_calls_correct_url(mock_get):
    """Tests that get_series() builds the correct URL from the base URL 
    and route. If the URL is malformed, every API call silently hits the 
    wrong endpoint. This test catches that by  inspecting what URL 
    request.get was called with.

    Args:
        mock_get (MagicMock): A mock object simulating a requests.Response
                                ingested by @patch so no real HTTP request
                                is made.

    Returns:
        None: Pass/fail determined by whether the assert statement raises 
                an AssertionError.
    """    
    mock_get.return_value = make_mock_response(mock_response)
    get_series("petroleum/sum/sndw")
    
    # Assert that requests.get was called with the correct URL and parameters
    # call_args[0][0] is the first positional argument (the URL)
    # call_args[1] is the keyword arguments (like params)
    call_args = mock_get.call_args
    assert "https://api.eia.gov/v2/petroleum/sum/sndw/data" in call_args[0][0]
    
    
@patch("ingestion.eia_client.requests.get")
def test_get_series_raises_on_http_error(mock_get):
    """Tests that get_series() raises an exception when the API returns an
    error. If the function swallows errors silently, bad data flows into the
    pipeline with no wanring. This test confirms loud failure on any HTTP error.

    Args:
        mock_get (MagicMock): Fake replacement for requests.get, injected
            by @patch so no real HTTP request is made.

    Returns:
        None: Pass/fail determined by pytest.raises() context manager.
    """    
    #.side_effect() means instead of returning a value, raise this exception to
    # simulate an HTTP error like 400 Bad Request. 
    mock_get.return_value = MagicMock()
    mock_get.return_value.raise_for_status.side_effect = Exception("400 Bad Request")
    
    # Assert and Act together: pytest.raises() checks that the code inside the
    # with block raisies the expected exception. match = checks the exception
    # message contains "400 Bad Request". If no exception or wrong message,
    # test fails.     
    with pytest.raises(Exception, match="400 Bad Request"):
        get_series("petroleum/sum/sndw")
        
############################################################
################# endpoint function tests ##################
############################################################

@patch("ingestion.eia_client.requests.get")
def test_get_cushing_stocks_returns_data(mock_get):
    """Tests that get_cushing_stocks() returns data filtered to Cushing
    crude oil. Checks both the duoarea code (YCUOK = Cushing, Oklahoma), 
    and the product code (EPCO = Crude Oil) to confirm facets are being 
    passed correctly.

    Args:
        mock_get (MagicMock): Fake replacement for requests.get, injected
            by @patch so no real HTTP request is made.

    Returns:
        None: Pass/fail determined by assert statements.
    """    
    mock_get.return_value = make_mock_response(mock_response)
    result = get_cushing_stocks(length=3)
    
    # Assert that confirms the location and product codes match
    # what we expect. If the API call is wrong, the wrong data lands
    # in the bronze table.
    assert result["response"]["data"][0]["duoarea"] == "YCUOK"
    assert result["response"]["data"][0]["product"] == "EPC0"
    
@patch("ingestion.eia_client.requests.get")
def test_get_cushing_stocks_value_is_present(mock_get):
    """Tests that get_cushing_stocks() returns a non-null storage volume
    value. Null values in Cushing stock data would break the storage pressure
    indicator calculation in the gold layer.

    Args:
        mock_get (MagicMock): Fake replacement for requests.get, injected
            by @patch so no real HTTP request is made.

    Returns:
        None: Pass/fail determined by assert statements.
    """    
    
    mock_get.return_value = make_mock_response(mock_response)
    result = get_cushing_stocks(length=3)
    
    # Assert that the 'value' key is present and not empty in the data
    assert "value" in result["response"]["data"][0] is not None   
    
    
@patch("ingestion.eia_client.requests.get")
def test_get_refinery_utilization_returns_data(mock_get):
    """Tests that get_refinery_utilization() returns data filtered to 
    US refinery, which is a dict with a response key.

    Args:
        mock_get (MagicMock): Fake replacement for requests.get, injected
            by @patch so no real HTTP request is made.

    Returns:
        None: Pass/fail determined by assert statements.
    """    
    mock_get.return_value = make_mock_response(mock_response)
    result = get_refinery_utilization(length=3)
    
    # Assert for basic structure checl to confirm the function returns
    # what the pipeline can unpack.
    assert isinstance(result, dict)
    assert "response" in result
    
    
@patch("ingestion.eia_client.requests.get")
def test_get_refinery_utilization_has_data(mock_get):
    """Tests that get_refinery_utilization() returns a non-empty data list.
    An empty lists means that the EPXXX2 product facet is filtering out
    everything, which would mean no refinery utilization data lands in the 
    bronze table.

    Args:
        mock_get (MagicMock): Fake replacement for requests.get, injected
            by @patch so no real HTTP request is made.

    Returns:
        None: Pass/fail determined by assert statements.
    """    
    
    mock_get.return_value = make_mock_response(mock_response)
    result = get_refinery_utilization(length=3)
    
    # Assert that the the data list must exist and have at least one record
    assert "data" in result["response"]
    assert len(result["response"]["data"]) > 0
    
    
@patch("ingestion.eia_client.requests.get")
def test_get_crude_imports_returns_dict(mock_get):
    """Tests that get_crude_imports() returns a dict with a response key.

    Args:
        mock_get (MagicMock): Fake replacement for requests.get, injected
            by @patch so no real HTTP request is made.

    Returns:
        None: Pass/fail determined by assert statements.
    """    
    mock_get.return_value = make_mock_response(mock_response)
    result = get_crude_imports(length=3)
    
    # Assert basic structure check
    assert isinstance(result, dict)
    assert "response" in result
    
    
@patch("ingestion.eia_client.requests.get")
def test_get_crude_imports_has_data(mock_get):
    """Tests that get_crude_imports() returns a non-empty data list. An
    empty list would mean that the EPCO product facet is misconfigured and
    no import data would reach the bronze layer.

    Args:
        mock_get (MagicMock): Fake replacement for requests.get, injected
            by @patch so no real HTTP request is made.

    Returns:
        None: Pass/fail determined by assert statements.
    """    
    
    mock_get.return_value = make_mock_response(mock_response)
    result = get_crude_imports(length=3)
    
    # Assert that the the data list must exist and have at least one record
    assert "data" in result["response"]
    assert len(result["response"]["data"]) > 0
    
    
    
@patch("ingestion.eia_client.requests.get")
def test_get_crude_production_returns_dict(mock_get):
    """Tests that get_crude_production() returns a dict with a response key.

    Args:
        mock_get (MagicMock): Fake replacement for requests.get, injected
            by @patch so no real HTTP request is made.

    Returns:
        None: Pass/fail determined by assert statements.
    """    
    mock_get.return_value = make_mock_response(mock_response)
    result = get_crude_production(length=3)
    
    # Assert basic structure check
    assert isinstance(result, dict)
    assert "response" in result
    
@patch("ingestion.eia_client.requests.get")
def test_get_crude_production_has_data(mock_get):
    """Tests that get_crude_production() returns a non-empty data list. An
    empty list would mean that the EPCO product facet is misconfigured and
    no production data would reach the bronze layer.

    Args:
        mock_get (MagicMock): Fake replacement for requests.get, injected
            by @patch so no real HTTP request is made.
    Returns:
        None: Pass/fail determined by assert statements.
    """    
    
    mock_get.return_value = make_mock_response(mock_response)
    result = get_crude_production(length=3)
    
    # Assert that the the data list must exist and have at least one record
    assert "data" in result["response"]
    assert len(result["response"]["data"]) > 0