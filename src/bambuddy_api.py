from urllib.parse import urlencode, urlsplit, urlunsplit
import requests

def normalize_url(value):
    value = value.strip().rstrip('/')
    parts = urlsplit(value)
    if parts.scheme not in ('http', 'https') or not parts.netloc or parts.username or parts.password:
        raise ValueError('Bitte eine vollständige http:// oder https:// Serveradresse eingeben.')
    if parts.query or parts.fragment:
        raise ValueError('Die Serveradresse darf keine Parameter oder Fragmente enthalten.')
    return value


def qr_link(base, spool_id):
    base = normalize_url(base)
    parts = urlsplit(base)
    path = parts.path.rstrip('/')
    if not path.endswith('/inventory'):
        path += '/inventory'
    return urlunsplit((parts.scheme, parts.netloc, path, urlencode({'spool': spool_id}), ''))


def fetch_spool(number, api_key, server):
    endpoint = normalize_url(server) + '/api/v1/inventory/spools'
    headers = {'X-API-Key': api_key, 'Authorization': f'Bearer {api_key}', 'Accept': 'application/json'}
    response = requests.get(endpoint, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError('BamBuddy hat keine Spulenliste geliefert.')
    return next((s for s in data if str(s.get('id')) == str(number)), None)
