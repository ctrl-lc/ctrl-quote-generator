from flask import Flask, request, make_response
from numpy_financial import pmt


UPDATE_DATE = '2021-01-14'

app = Flask(__name__)


@app.route("/quote")
def get_quote():

    error_message, error_code = check_params()
    if error_message is None:
        return calc_payment()
    else:
        return make_response(error_message, error_code)


def check_params():

    CHECKS = [check_missing_params, check_vehicle_type, check_numericals,
              check_vat, check_brands, check_year_for_russian_trucks]

    for check in CHECKS:
        result = check()
        if result:
            return result

    return None, None


def check_missing_params():
    REQUIRED_PARAMS = {'vehicle_type', 'year', 'VAT_included', 'downpayment',
                    'price', 'brand'}

    missing_params = REQUIRED_PARAMS - set(request.args.keys())
    if missing_params:
        return f'Missing parameters: {", ".join(missing_params)}.', 400


def check_vehicle_type():
    VEHICLE_TYPES = ['semitruck', 'semitrailer']

    if request.args['vehicle_type'] not in VEHICLE_TYPES:
        return (f'`vehicle_type` should be one of: '
                f'{", ".join(VEHICLE_TYPES)}', 400)


def check_numericals():
    NUMERICALS = {
        'year': (int, 2016, 2021),
        'downpayment': (float, 0, 0.49999),
        'price': (int, 1_000_000, 10_000_000)
    }

    for key, values in NUMERICALS.items():
        type_, min_, max_ = values

        try:
            value = type_(request.args[key])
        except ValueError:
            return f'`{key}` should be a {type_}, ' \
                f'but now it is "{request.args[key]}".', 400

        if not min_ <= value <= max_:
            return f'`{key}` should be between {min_} and {max_}, ' \
                f'but now it is "{request.args[key]}".', 400


def check_vat():
    vat = request.args['VAT_included']
    try:
        convert_to_bool(vat)
    except ValueError:
        return f'`VAT_included` should be a bool, but now it is "{vat}".', 400


def convert_to_bool(value: str):
    if value.lower() in ['yes', 'true', '1']:
        return True
    if value.lower() in ['no', 'false', '0', '-1']:
        return False
    raise ValueError(f'"{value}" could not be converted to bool')


def check_brands():
    BRANDS = {
        # semitrucks
        'KAMAZ', 'MAZ', 'MAN', 'DAF', 'MERCEDES', 'VOLVO', 'SCANIA', 'RENAULT',
        'IVECO',
        # semitrailers
        'MAZ', 'SCHMITZ', 'KOGEL', 'NEFAZ'
    }

    if request.args['brand'] not in BRANDS:
        return f"`brand` should be one of: {', '.join(BRANDS)}, " \
                f"but now it is `{request.args['brand']}`.", 400


def check_year_for_russian_trucks():
    if request.args['vehicle_type'] == 'semitruck' \
            and request.args['brand'] in ['KAMAZ', 'MAZ'] \
            and not 2018 <= int(request.args['year']) <= 2021:
        return 'For truck brands "KAMAZ" and "MAZ" ' \
            '`year` should be >= 2018 and <= 2020', 400


def calc_payment() -> int:
    BASE_RATE = 0.13
    VAT_RATE = 0.2
    PERIODS = 48

    price = int(request.args['price'])
    downpayment = float(request.args['downpayment'])
    VAT_included = convert_to_bool(request.args['VAT_included'])

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
