import requests
from src.config.settings.base import KEYCLOAK
from django.conf import settings
from .keycloak_urls import kc_url

def login(username, password):
    url = kc_url(KEYCLOAK["TOKEN_ENDPOINT"])
    data = {
        "grant_type": "password",
        "client_id": KEYCLOAK["CLIENT_ID"],
        "client_secret": KEYCLOAK["CLIENT_SECRET"],
        "username": username,
        "password": password,
    }
    print("Request URL:", url)
    print("Request Data:", data)
    r = requests.post(url, data=data, timeout=10)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("HTTP Error:", r.status_code, r.text)
        raise
    return r.json()


def refresh(refresh_token):
    r = requests.post(
        kc_url(KEYCLOAK["TOKEN_ENDPOINT"]),
        data={
            "grant_type": "refresh_token",
            "client_id": KEYCLOAK["CLIENT_ID"],
            "client_secret": KEYCLOAK["CLIENT_SECRET"],
            "refresh_token": refresh_token,
        },
        timeout=5,
    )
    r.raise_for_status()
    return r.json()

def logout(refresh_token):
    requests.post(
        kc_url(KEYCLOAK["LOGOUT_ENDPOINT"]),
        data={
            "client_id": KEYCLOAK["CLIENT_ID"],
            "client_secret": KEYCLOAK["CLIENT_SECRET"],
            "refresh_token": refresh_token,
        },
        timeout=5,
    )

def get_userinfo(access_token):
    r = requests.get(
        kc_url(KEYCLOAK["USERINFO_ENDPOINT"]),
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()

def public_keys():
    r = requests.get(
        kc_url(KEYCLOAK["JWKS_ENDPOINT"]),
        timeout=5,
    )
    r.raise_for_status()
    return r.json()

def choose_key(kid):
    keys = public_keys()
    for key in keys["keys"]:
        if key["kid"] == kid:
            return key
    raise Exception("Key not found")

def get_admin_token():
    r = requests.post(
        f"{KEYCLOAK['BASE_URL']}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": "admin",
            "password": "admin",
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def get_service_account_token():
    r = requests.post(
        kc_url(KEYCLOAK["TOKEN_ENDPOINT"]),
        data={
            "grant_type": "client_credentials",
            "client_id": KEYCLOAK["SA_CLIENT_ID"],
            "client_secret": KEYCLOAK["SA_CLIENT_SECRET"],
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def create_user(username, password, email="", first_name="", last_name=""):
    token = get_service_account_token()

    url = f"{KEYCLOAK['BASE_URL']}/admin/realms/{KEYCLOAK['REALM']}/users"

    payload = {
        "username": username,
        "enabled": True,
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "credentials": [
            {
                "type": "password",
                "value": password,
                "temporary": False,
            }
        ],
    }

    r = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )

    if r.status_code not in (201, 204):
        raise Exception(f"Keycloak error: {r.status_code} {r.text}")

    return True

def delete_user(username):
    token = get_service_account_token()

    url = f"{KEYCLOAK['BASE_URL']}/admin/realms/{KEYCLOAK['REALM']}/users"

    r = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
        },
        params={"username": username},
        timeout=10,
    )

    r.raise_for_status()
    users = r.json()

    if not users:
        raise Exception("User not found")

    user_id = users[0]["id"]

    r = requests.delete(
        f"{url}/{user_id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=10,
    )

    if r.status_code not in (204,):
        raise Exception(f"Keycloak error: {r.status_code} {r.text}")

    return True


def get_google_login_url():
    """Restituisce l'URL dove redirectare l'utente per login Google tramite Keycloak"""
    from django.conf import settings

    url = (
        f"{KEYCLOAK['BASE_URL']}/realms/{KEYCLOAK['REALM']}/protocol/openid-connect/auth"
        f"?client_id={KEYCLOAK['CLIENT_WEB_ID']}"
        f"&redirect_uri=http://localhost:8000/auth/callback"
        f"&response_type=code"
        f"&scope=openid"
        f"&kc_idp_hint=google"
    )
    return url

def exchange_code_for_token(code):
    """Scambia il code restituito da Keycloak con i token"""
    import requests
    from django.conf import settings

    token_url = f"{KEYCLOAK['BASE_URL']}/realms/{KEYCLOAK['REALM']}/protocol/openid-connect/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": KEYCLOAK["CLIENT_ID"],
        "client_secret": KEYCLOAK["CLIENT_SECRET"],
        "code": code,
        "redirect_uri": "http://localhost:8000/auth/callback",
    }

    r = requests.post(token_url, data=data, timeout=10)
    r.raise_for_status()
    return r.json()

