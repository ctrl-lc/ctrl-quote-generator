from flask import Flask, make_response, request
from icontract import ViolationError, require
from numpy_financial import pmt
from pydantic import BaseModel, ValidationError, validator

UPDATE_DATE = "2021-02-04"

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

    @validator("vehicle_type")
    def vehicle_type_lower(cls, v):
        return v.strip().lower()

    @validator("brand")
    def brand_upper(cls, v):
        return v.strip().upper()


def check_params(params: CalcParams):

    CHECKS = [
        check_vehicle_type,
        check_numericals,
        check_year_for_russian_vehicles,
        no_chinese_brands,
    ]

    for check in CHECKS:
        check(**params.dict())


@require(
    lambda vehicle_type: vehicle_type in ["semitrailer", "semitruck", "dump_truck"],
    "Only 'semitruck', 'semitrailer' or 'dump_truck' are supported as vehicle_type",
)
def check_vehicle_type(vehicle_type, **args):
    pass


@require(lambda year: 2016 <= year <= 2021)
@require(lambda downpayment: 0 <= downpayment < 0.5)
@require(lambda price: 1_000_000 <= price <= 20_000_000)
def check_numericals(year, downpayment, price, **args):
    pass


BIG_SEVEN = {
    "MAN",
    "DAF",
    "MERCEDES",
    "VOLVO",
    "SCANIA",
    "RENAULT",
    "IVECO",
}

EUROPEAN_BRANDS = BIG_SEVEN | {"SCHMITZ", "KOGEL", "KOLUMAN", "GRUNWALD", "KASSBOHRER"}

RUSSIAN_BRANDS = {"MAZ", "KAMAZ", "NEFAZ", "TONAR"}

ALLOWED_BRANDS = EUROPEAN_BRANDS | RUSSIAN_BRANDS

@require(
    lambda vehicle_type, brand, year: 2018 <= int(year) <= 2021
    if brand in RUSSIAN_BRANDS
    else True,
    "For Russian brands the `year` should be >= 2018 and <= 2021",
)
def check_year_for_russian_vehicles(vehicle_type, brand, year, **args):
    pass


@require(
    lambda brand: brand in ALLOWED_BRANDS,
    "Only Russian and European brands are allowed, no Chinese",
)
def no_chinese_brands(brand, **args):
    pass


def calc_payment(price: int, downpayment: float, VAT_included: bool, **args) -> int:
    BASE_RATE = 0.13
    VAT_RATE = 0.2
    PERIODS = 48

    nim = 0.1 if downpayment < 0.1 else 0.07

    rate = (BASE_RATE + nim) * (1 + VAT_RATE)

    price_plus_VAT = price if VAT_included else price * (1 + VAT_RATE)
    investment_plus_VAT = price_plus_VAT * (1 - downpayment)

    return {
        "downpayment": {
            "value": int(downpayment * price_plus_VAT),
            "VAT_included": True,
        },
        "monthly_payment": {
            "value": int(-pmt(rate / 12, PERIODS, investment_plus_VAT)),
            "VAT_included": True,
        },
    }


@app.route("/calc_update_date")
def calc_update_date():
    return UPDATE_DATE


@app.route("/brands")
def get_brand_list():
    return {"brands": list(ALLOWED_BRANDS)}
