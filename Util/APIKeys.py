API_KEY='ApaMmGBHGTWD1QYTdLAPvSEgiA16CmEQ'
API_SECRET='v6AuJJqFvI6vpnwS'

import requests

url = "https://test.api.amadeus.com/v1/security/oauth2/token"
headers = {
    "Content-Type": "application/x-www-form-urlencoded"
}
data = {
    "grant_type": "client_credentials",
    "client_id": "ApaMmGBHGTWD1QYTdLAPvSEgiA16CmEQ",
    "client_secret": "v6AuJJqFvI6vpnwS"
}

response = requests.post(url, headers=headers, data=data)
def get_acces_token():
    # Check the response status code
    if response.status_code == 200:
        data = response.json()
        # Process the data as needed
        return data['access_token']
    else:
        print("Error:", response.status_code)
    return -1

