from flask import Flask, make_response, request
from icontract import ViolationError, require
from numpy_financial import pmt
from pydantic import BaseModel, ValidationError

UPDATE_DATE = '2021-01-15'

app = Flask(__name__)


@app.route("/quote")
def get_quote():

    try:
        params = CalcParams(**request.args)
        check_params(params)

    except (ValidationError, ViolationError) as err:
        return make_response(str(err), 400)

    return calc_payment(**params.dict())


class CalcParams(BaseModel):
    vehicle_type: str
    brand: str
    year: int
    price: int
    downpayment: float
    VAT_included: bool


def check_params(params: CalcParams):

    CHECKS = [check_vehicle_type, check_numericals,
              check_brand, check_year_for_russian_trucks]

    for check in CHECKS:
        check(**params.dict())


@require(lambda vehicle_type: vehicle_type.lower()
         in ['semitrailer', 'semitruck'],
         "Only semitrucks or semtrailers supported as vehicle_type")
def check_vehicle_type(vehicle_type, **args):
    pass


@require(lambda year: 2016 <= year <= 2021)
@require(lambda downpayment: 0 <= downpayment < 0.5)
@require(lambda price: 1_000_000 <= price <= 20_000_000)
def check_numericals(year, downpayment, price, **args):
    pass


BRANDS = {
    # semitrucks
    'KAMAZ', 'MAZ', 'MAN', 'DAF', 'MERCEDES', 'VOLVO', 'SCANIA', 'RENAULT',
    'IVECO',
    # semitrailers
    'MAZ', 'SCHMITZ', 'KOGEL', 'NEFAZ'
}


@require(lambda brand: brand in BRANDS)
def check_brand(brand, **args):
    pass


@require(
    lambda vehicle_type, brand, year:
    vehicle_type != 'semitruck' or brand not in ['KAMAZ', 'MAZ']
    or 2018 <= int(year) <= 2021,
    'For truck brands "KAMAZ" and "MAZ" `year` should be >= 2018 and <= 2021')
def check_year_for_russian_trucks(vehicle_type, brand, year, **args):
    pass


def calc_payment(price: int, downpayment: float,
                 VAT_included: bool, **args) -> int:
    BASE_RATE = 0.13
    VAT_RATE = 0.2
    PERIODS = 48

    nim = 0.1 if downpayment < 0.1 else 0.07

    rate = (BASE_RATE + nim) * (1 + VAT_RATE)

    price_plus_VAT = price if VAT_included else price * (1 + VAT_RATE)
    investment_plus_VAT = price_plus_VAT * (1 - downpayment)

    return {
        'downpayment': {
            'value': int(downpayment * price_plus_VAT),
            'VAT_included': True
        },
        'monthly_payment': {
            'value': int(-pmt(rate/12, PERIODS, investment_plus_VAT)),
            'VAT_included': True
        }
    }


@app.route('/calc_update_date')
def calc_update_date():
    return UPDATE_DATE
