from collections import namedtuple
from icontract import require, ViolationError
from flask import Flask, request, make_response
from numpy_financial import pmt


UPDATE_DATE = '2021-01-16'

app = Flask(__name__)


@app.route("/quote")
def get_quote():

    try:
        check_params(request.args)
    except ViolationError as err:
        return make_response(str(err), 400)

    calc_params = extract_calc_params(**request.args)
    return calc_payment(**calc_params._asdict())


REQUIRED_PARAMS = {'vehicle_type', 'year', 'VAT_included', 'downpayment',
                   'price', 'brand'}


@require(lambda args: args and not(REQUIRED_PARAMS - set(args.keys())),
         'Missing required parameters')
def check_params(args: dict):

    CHECKS = [check_vehicle_type, check_numericals,
              check_vat, check_brand, check_year_for_russian_trucks]

    for check in CHECKS:
        check(**args)


@require(lambda vehicle_type: vehicle_type.lower()
         in ['semitrailer', 'semitruck'],
         "Only semitrucks or semtrailers supported as vehicle_type")
def check_vehicle_type(vehicle_type, **args):
    pass


def check_numericals(year, downpayment, price, **args):

    @require(lambda year: 2016 <= year <= 2021)
    @require(lambda downpayment: 0 <= downpayment < 5)
    @require(lambda price: 1_000_000 <= price <= 20_000_000)
    def check_transformed(year: int, downpayment: float, price: int):
        pass

    try:
        check_transformed(year=int(year), downpayment=float(downpayment),
                          price=int(price))
    except ValueError:
        raise ViolationError(
            'year, downpayment or price has a wrong type')


def check_vat(VAT_included, **args):
    convert_to_bool(VAT_included)


def convert_to_bool(value: str):
    if value.lower() in ['yes', 'true', '1']:
        return True
    if value.lower() in ['no', 'false', '0', '-1']:
        return False
    raise ViolationError(
        f'VAT_included value ("{value}") could not be converted to bool')


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


CalcParams = namedtuple('CalcParams', ['price', 'downpayment', 'VAT_included'])


def extract_calc_params(price, downpayment, VAT_included, **args):
    return CalcParams(int(price), float(downpayment),
                      convert_to_bool(VAT_included))


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
