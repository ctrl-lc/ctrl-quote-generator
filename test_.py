from urllib.parse import urlencode
from hypothesis.control import assume

import pytest
from hypothesis import given
import hypothesis.strategies as st


from quoter import app, check_numericals, check_params, calc_payment


@pytest.fixture
def client():
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client


def test_normal(client):
    params = {
        'vehicle_type': 'semitrailer',
        'year': 2016,
        'downpayment': 0.1,
        'VAT_included': 'yes',
        'price': 5_000_000,
        'brand': 'MAN'
    }
    resp = client.get("/quote?" + urlencode(params))
    assert resp.status_code == 200


@given(st.dictionaries(st.text(), st.text()))
def test_check_random_params(params):

    assert check_params(**params) != (None, None)


@given(price=st.integers(), downpayment=st.floats(), year=st.integers())
def test_check_numericals(price, downpayment, year):

    check_numericals(price=str(price), downpayment=str(downpayment),
                     year=str(year))


@given(price=st.integers(1, 10_000_000),
       downpayment=st.floats(0.000001, 0.4999999999),
       VAT_included=st.booleans(), year=st.integers(2016, 2021))
def test_calc(price, downpayment, VAT_included, year):

    assume(check_numericals(
        price=price, downpayment=downpayment, year=year) is None)

    payments = calc_payment(price, downpayment, VAT_included)

    assert payments['monthly_payment']['value'] > 0
    assert payments['downpayment']['value'] >= 0
    assert payments['monthly_payment']['VAT_included']
    assert payments['downpayment']['VAT_included']
