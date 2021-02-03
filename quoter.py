from flask import Flask, make_response, request
from icontract import ViolationError, require
from numpy_financial import pmt
from pydantic import BaseModel, ValidationError, validator

UPDATE_DATE = "2021-01-25"

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
        check_brand,
        check_year_for_worse_trucks,
    ]

    for check in CHECKS:
        check(**params.dict())


@require(
    lambda vehicle_type: vehicle_type in ["semitrailer", "semitruck", "dump_truck"],
    "Only 'semitruck', 'semtrailer' or 'dump_truck' "
    "are supported as vehicle_type",
)
def check_vehicle_type(vehicle_type, **args):
    pass


@require(lambda year: 2016 <= year <= 2021)
@require(lambda downpayment: 0 <= downpayment < 0.5)
@require(lambda price: 1_000_000 <= price <= 20_000_000)
def check_numericals(year, downpayment, price, **args):
    pass


TRUCK_BRANDS = {
    "KAMAZ",
    "MAZ",
    "MAN",
    "DAF",
    "MERCEDES",
    "VOLVO",
    "SCANIA",
    "RENAULT",
    "IVECO",
}

TRAILER_BRANDS = {"MAZ", "SCHMITZ", "KOGEL", "NEFAZ", "TONAR"}


@require(
    lambda brand, vehicle_type: (
        brand in TRAILER_BRANDS if vehicle_type == "semitrailer" else True
    ),
    "Wrong semitrailer brand",
)
@require(
    lambda brand, vehicle_type: (
        brand in TRUCK_BRANDS if vehicle_type == "semitruck" else True
    ),
    "Wrong semitruck brand",
)
def check_brand(brand, vehicle_type, **args):
    pass


@require(
    lambda vehicle_type, brand, year: 2018 <= int(year) <= 2021
    if vehicle_type == "semitruck" and brand in ["KAMAZ", "MAZ", "IVECO"]
    else True,
    'For truck brands "KAMAZ", "MAZ" and "IVECO" `year` should be >= 2018 and <= 2021',
)
def check_year_for_worse_trucks(vehicle_type, brand, year, **args):
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
