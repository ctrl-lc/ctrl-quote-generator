from urllib.parse import urlencode

import pytest


from quoter import app

@pytest.fixture
def client():
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client


def test_missing_brand(client):
    params = {
        'vehicle_type': 'semitrailer',
        'year': 2016,
        'downpayment': 0.1,
        'VAT_included': 'yes',
        'price': 5_000_000
    }
    resp = client.get("/quote?" + urlencode(params))
    assert resp.status_code == 400 and 'brand' in str(resp.data)
