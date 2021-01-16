from urllib.parse import urlencode

import hypothesis.strategies as st
import pytest
from hypothesis import assume, given
from icontract import ViolationError
from pydantic import ValidationError

from quoter import (CalcParams, app, calc_payment, check_numericals,
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
        'brand': 'MAZ'
    }
    resp = client.get("/quote?" + urlencode(params))
    assert resp.status_code == 200


@given(st.dictionaries(st.text(), st.text()))
def test_check_random_params(params):

    with pytest.raises(ValidationError):
        CalcParams(**params)


@given(price=st.integers(1_000_000, 10_000_000),
       downpayment=st.floats(0, 0.5),
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


@given(st.integers(2016, 2021), st.floats(0, 0.5),
       st.integers(1_000_000, 20_000_000))
def test_numericals_success(year, downpayment, price):
    check_numericals(year, downpayment, price)


def test_numericals_fails():
    with pytest.raises(ViolationError):
        check_numericals(2020, 0, 5)

    with pytest.raises(ViolationError):
        check_numericals(2030, 0, 5_000_000)

    with pytest.raises(ViolationError):
        check_numericals(2020, 0.5, 5_000_000)

    with pytest.raises(ViolationError):
        check_numericals(2015, 0, 5_000_000)
