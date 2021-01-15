from collections import namedtuple
from flask import Flask, request, make_response
from numpy_financial import pmt


UPDATE_DATE = '2021-01-15'

app = Flask(__name__)


@app.route("/quote")
def get_quote():

    error_message, error_code = check_params(**request.args)
    if error_message is not None:
        return make_response(error_message, error_code)

    calc_params = extract_calc_params(**request.args)
    return calc_payment(**calc_params._asdict())


def check_params(**args):

    CHECKS = [check_missing_params, check_vehicle_type, check_numericals,
              check_vat, check_brand, check_year_for_russian_trucks]

    for check in CHECKS:
        result = check(**args)
        if result:
            return result

    return None, None


def check_missing_params(**args):
    REQUIRED_PARAMS = {'vehicle_type', 'year', 'VAT_included', 'downpayment',
                       'price', 'brand'}

    missing_params = REQUIRED_PARAMS - set(args.keys())
    if missing_params:
        return f'Missing parameters: {", ".join(missing_params)}.', 400


def check_vehicle_type(vehicle_type, **args):
    VEHICLE_TYPES = ['semitruck', 'semitrailer']

    if vehicle_type not in VEHICLE_TYPES:
        return (f'`vehicle_type` should be one of: '
                f'{", ".join(VEHICLE_TYPES)}', 400)


def check_numericals(**args):
    NUMERICALS = {
        'year': (int, 2016, 2021),
        'downpayment': (float, 0, 0.49999),
        'price': (int, 1_000_000, 10_000_000)
    }

    for key, values in NUMERICALS.items():
        type_, min_, max_ = values

        try:
            value = type_(args[key])
        except ValueError:
            return f'`{key}` should be a {type_}, ' \
                f'but now it is "{args[key]}".', 400

        if not min_ <= value <= max_:
            return f'`{key}` should be between {min_} and {max_}, ' \
                f'but now it is "{args[key]}".', 400


def check_vat(VAT_included, **args):
    try:
        convert_to_bool(VAT_included)
    except ValueError:
        return (f'`VAT_included` should be a bool, '
                f'but now it is "{VAT_included}".', 400)


def convert_to_bool(value: str):
    if value.lower() in ['yes', 'true', '1']:
        return True
    if value.lower() in ['no', 'false', '0', '-1']:
        return False
    raise ValueError(f'"{value}" could not be converted to bool')


def check_brand(brand, **args):
    BRANDS = {
        # semitrucks
        'KAMAZ', 'MAZ', 'MAN', 'DAF', 'MERCEDES', 'VOLVO', 'SCANIA', 'RENAULT',
        'IVECO',
        # semitrailers
        'MAZ', 'SCHMITZ', 'KOGEL', 'NEFAZ'
    }

    if brand not in BRANDS:
        return f"`brand` should be one of: {', '.join(BRANDS)}, " \
                f"but now it is `{brand}`.", 400


def check_year_for_russian_trucks(vehicle_type, brand, year, **args):
    if vehicle_type == 'semitruck' \
            and brand in ['KAMAZ', 'MAZ'] \
            and not 2018 <= int(year) <= 2021:
        return 'For truck brands "KAMAZ" and "MAZ" ' \
            '`year` should be >= 2018 and <= 2020', 400


def extract_calc_params(price, downpayment, VAT_included, **args):
    CalcParams = namedtuple('CalcParams', ['price', 'downpayment',
                                           'VAT_included'])
    return CalcParams(int(price), float(downpayment),
                      convert_to_bool(VAT_included))


def calc_payment(price, downpayment, VAT_included, **args) -> int:
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
