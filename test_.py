from urllib.parse import urlencode

import hypothesis.strategies as st
import pytest
from hypothesis import given, assume
from icontract import ViolationError

from quoter import (app, calc_payment, check_numericals, check_params,
                    check_year_for_russian_trucks)


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

    with pytest.raises(ViolationError):
        check_params(params)


@given(price=st.integers(), downpayment=st.floats(), year=st.integers())
def test_check_numericals(price, downpayment, year):

    with pytest.raises(ViolationError):
        check_numericals(price=str(price), downpayment=str(downpayment),
                         year=str(year))


@given(price=st.integers(1_000_000, 10_000_000),
       downpayment=st.floats(0.000001, 0.4999999999),
       VAT_included=st.booleans(), year=st.integers(2016, 2021))
def test_calc(price, downpayment, VAT_included, year):

    try:
        check_numericals(
            price=price, downpayment=downpayment, year=year)
    except ViolationError:
        assume(False)

    payments = calc_payment(price, downpayment, VAT_included)

    assert payments['monthly_payment']['value'] > 0
    assert payments['downpayment']['value'] >= 0
    assert payments['monthly_payment']['VAT_included']
    assert payments['downpayment']['VAT_included']


def test_russian_trucks():
    check_year_for_russian_trucks('semitruck', 'KAMAZ', 2020)
    check_year_for_russian_trucks('semitruck', 'MAN', 2016)

    with pytest.raises(ViolationError):
        check_year_for_russian_trucks('semitruck', 'MAZ', 2016)


def test_numericals_transformation():
    check_numericals('2020', '0.1', '2000000')
    with pytest.raises(ViolationError):
        check_numericals('xxx', '0.1', '2000000')
