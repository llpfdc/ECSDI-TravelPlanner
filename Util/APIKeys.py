API_KEY_FLIGHT='ApaMmGBHGTWD1QYTdLAPvSEgiA16CmEQ'
API_SECRET_FLIGHT='v6AuJJqFvI6vpnwS'

import requests


def get_acces_token_flight():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials",
        "client_id": API_KEY_FLIGHT,
        "client_secret": API_SECRET_FLIGHT
    }

    response = requests.post(url, headers=headers, data=data)
    # Check the response status code
    if response.status_code == 200:
        data = response.json()
        # Process the data as needed
        return data['access_token']
    else:
        print("Error:", response.status_code)
    return -1

API_KEY_HOTEL='55JQbVQzuw2hCKPJbUeeyDYysSJfOPBm'
API_SECRET_HOTEL='rMEtLZbFLbgZOVLQ'

def get_acces_token_hotel():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials",
        "client_id": API_KEY_HOTEL,
        "client_secret": API_SECRET_HOTEL
    }

    response = requests.post(url, headers=headers, data=data)
    # Check the response status code
    if response.status_code == 200:
        data = response.json()
        # Process the data as needed
        return data['access_token']
    else:
        print("Error:", response.status_code)
    return -1

API_KEY_ACTIVITIES='5X4VjYbWOqdnuUSukZ8RPGHxSkrEN2pV'
API_SECRET_ACTIVITIES='XVvgfaVLGFDqhISc'
def get_acces_token_activities():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials",
        "client_id": API_KEY_ACTIVITIES,
        "client_secret": API_SECRET_ACTIVITIES
    }

    response = requests.post(url, headers=headers, data=data)
    # Check the response status code
    if response.status_code == 200:
        data = response.json()
        # Process the data as needed
        return data['access_token']
    else:
        print("Error:", response.status_code)
    return -1