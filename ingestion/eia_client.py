import requests
import os
from dotenv import load_dotenv
from typing import Optional

# reads .env file and sets environment variables
load_dotenv()

EIA_base_url = "https://api.eia.gov/v2"
api_key = os.getenv("EIA_API_KEY")

def get_series(route: str, facets: Optional[dict] = None, length: int = 52) -> dict:    
    """
    Pull a time series from the EIA API based on the specified route and facets.

    Args:
        route (str): The EIA endpoint path (e.g., "petroleum/sum/sndw").
        facets (dict): Optional filters to apply like PADD region (Petroleum Administration 
                        for Defense Districts) or product type.
        length (int): How many weekly periods to periods to retrieve (default is 52 for one year).

    Returns:
        dict: Raw JSON response as a python dictionary.
    """
    url = f"{EIA_base_url}/{route}/data"
    
    params = [
        ("api_key", api_key),
        ("frequency", "weekly"),
        ("data[0]", "value"),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "desc"),
        ("length", length),
    ]
    # filter by things like PADD region or product type if facets are provided
    # e.g., {"duoarea": ["R10"]} for PADD 1 crude oil inventories
    if facets:
        for key, values in facets.items():
            for val in values:
                params.append((f"facets[{key}][]", val))
                
    response = requests.get(url, params=params)
    
    # throws an exception immediately if the API returns a 4xx or 5xx error
    response.raise_for_status()  # raise an error if the request was unsuccessful
    
    return response.json()


def get_cushing_stocks(length: int=52) -> dict:
    """
    Weekly crude oil stocks at Cushing, Oklahoma. Cushing is the physical delivery point
    for WTI (West Texas Intermediate) crude oil. Storage levels can impact prices significantly.
    When storage fills up, prices crash. When it drains, supply is tight.

    Args:
        length (int): How many weekly periods to retrieve (default is 52 for one year).

    Returns:
        dict: Raw JSON response as a python dictionary.
    """
    return get_series(
        route="petroleum/sum/sndw",
        facets={"duoarea": ["YCUOK"], "product": ["EPC0"]},
        length=length
    )

def get_refinery_utilization(length: int=52) -> dict:
    """
    Weekly refinery utilization rates in the US by PADD region. We pull gross inputs (EPXXX2) 
    rather than the self-reported utilization percentage because we want to compute our own
    efficiency metric against nameplate capacity.

    Args:
        length (int): How many weekly periods to retrieve (default is 52 for one year).

    Returns:
        dict: Raw JSON response as a python dictionary.
    """
    route = "petroleum/pnp/wiup"
    facets = {"product": ["EPXXX2"]} # product code for crude oil, and location code for the whole US.
    
    return get_series(route, facets, length)


def get_crude_imports(length: int=52) -> dict:
    """
    Weekly crude oil imports into the US Weekly crude oil imports by country of origin.
    Different countries produce crude of different API gravity: Canadian heavy, Saudi medium, 
    Nigerian light sweet. This feeds the feedstock quality match score.

    Args:
        length (int): How many weekly periods to retrieve (default is 52 for one year).

    Returns:
        dict: Raw JSON response as a python dictionary.
    """
    return get_series(
        route="petroleum/move/wimpc",
        facets={"product": ["EPC0"]},
        length=length
    )


def get_crude_production(length: int=52) -> dict:
    """
    Weekly US field production of crude oil. This shows how much crude oil is being 
    produced domestically. High production can indicate strong supply, while low
    production can indicate supply constraints.

    Args:
        length (int): How many weekly periods to retrieve (default is 52 for one year).

    Returns:
        dict: Raw JSON response as a python dictionary.
    """
    return get_series(
        route="petroleum/sum/sndw",
        facets={"duoarea": ["NUS"], "product": ["EPC0"], "process": ["FPF"]},
        length=length
    )