from strands import tool
import requests

@tool
def search_receipt(api_key: str, merchant_id: str, offset: int = 0, limit: int = 10) -> dict:
    """
    Search for receipts for a merchant by calling the Slyp API.
    Args:
        api_key: The API key for authentication (required).
        merchant_id: The merchant's unique identifier (required).
        offset: The offset for pagination (default 0)
        limit: The maximum number of receipts to return (default 10)
    Returns:
        A dictionary containing the receipts or error information.
    """
    # First, authenticate to get JWT token
    auth_url = "https://api.team-slyp.com.au/v1/authenticate"
    auth_payload = {
        "apiKey": api_key,
        "requiredRole": {"merchant_default": merchant_id}
    }
    
    try:
        # Get authentication token
        auth_response = requests.post(auth_url, json=auth_payload)
        auth_response.raise_for_status()
        auth_data = auth_response.json()
        jwt_token = auth_data.get("jwt_token")
        
        if not jwt_token:
            return {"error": "Failed to retrieve JWT token from authentication response"}
        
        # Now make the receipts request with the JWT token
        url = f"https://api.team-slyp.com.au/v1/merchants/{merchant_id}/receipts"
        params = {"offset": offset, "limit": 1}
        headers = {"Authorization": f"Bearer {jwt_token}"}
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}
