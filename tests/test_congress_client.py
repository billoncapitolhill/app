import pytest
from unittest.mock import patch
from src.services.congress_client import CongressClient

@patch('src.services.congress_client.requests.get')
def test_get_bill_amendments_success(mock_get):
    mock_response = {
        "amendments": [
            {"type": "HAMDT", "number": "173"},
            {"type": "SAMDT", "number": "174"}
        ]
    }
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_response

    client = CongressClient(api_key="test_key")
    amendments = client.get_bill_amendments(118, "HR", "9775")

    assert len(amendments) == 2
    assert amendments[0]["type"] == "HAMDT"
    assert amendments[1]["number"] == "174"

@patch('src.services.congress_client.requests.get')
def test_get_bill_amendments_not_found(mock_get):
    mock_get.return_value.status_code = 404
    mock_get.return_value.json.return_value = {"error": "Unknown resource"}

    client = CongressClient(api_key="test_key")
    amendments = client.get_bill_amendments(118, "HR", "9775")

    assert amendments == [] 