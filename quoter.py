from typing import Optional
from flask import Flask, make_response, request
from icontract import ViolationError, require
from numpy_financial import pmt
from pydantic import BaseModel, ValidationError, validator

UPDATE_DATE = "2021-02-05"

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
    vehicle_subtype: Optional[str]
    brand: str
    year: int
    price: int
    downpayment: float
    VAT_included: bool

    @validator("vehicle_type")
    def vehicle_type_lower(cls, v):
        return v.strip().lower()

    @validator("vehicle_subtype")
    def vehicle_subtype_lower(cls, v):
        return v.strip().lower()

    @validator("brand")
    def brand_upper(cls, v):
        return v.strip().upper()


def check_params(params: CalcParams):

    CHECKS = [
        check_vehicle_type,
        check_vehicle_subtype,
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


ATI_SUBTYPES = {
    "1": "тентованный",
    "2": "контейнер",
    "3": "фургон",
    "4": "цельнометалл.",
    "5": "изотермический",
    "6": "рефрижератор",
    "7": "реф. мультирежимный",
    "8": "реф. с перегородкой",
    "9": "реф.-тушевоз",
    "10": "бортовой",
    "11": "открытый конт.",
    "12": "площадка без бортов",
    "13": "самосвал",
    "14": "шаланда",
    "15": "низкорамный",
    "16": "низкорам.платф.",
    "17": "телескопический",
    "18": "трал",
    "19": "балковоз(негабарит)",
    "20": "автобус",
    "21": "автовоз",
    "22": "автовышка",
    "23": "автотранспортер",
    "24": "бетоновоз",
    "25": "битумовоз",
    "26": "бензовоз",
    "27": "вездеход",
    "28": "газовоз",
    "29": "зерновоз",
    "30": "коневоз",
    "31": "конт.площадка",
    "32": "кормовоз",
    "33": "кран",
    "34": "лесовоз",
    "35": "ломовоз",
    "36": "манипулятор",
    "37": "микроавтобус",
    "38": "муковоз",
    "39": "панелевоз",
    "40": "пикап",
    "41": "пухтовоз",
    "42": "пирамида",
    "43": "рулоновоз",
    "44": "седельный тягач",
    "45": "скотовоз",
    "46": "стекловоз",
    "47": "трубовоз",
    "48": "цементовоз",
    "49": "цистерна",
    "50": "щеповоз",
    "51": "эвакуатор",
    "52": "грузопассажирский",
    "53": "клюшковоз",
    "54": "мусоровоз",
    "55": "юмбо",
}

ALLOWED_SYBTYPES = {
    "1": "тентованный",
    "5": "изотермический",
    "6": "рефрижератор",
    "7": "реф. мультирежимный",
    "8": "реф. с перегородкой",
    "9": "реф.-тушевоз",
    "10": "бортовой",
    "13": "самосвал",
    "44": "седельный тягач",
}


@require(
    lambda vehicle_subtype: vehicle_subtype in ATI_SUBTYPES.values() if vehicle_subtype else True,
    "This vehicle_subtype is unknown",
)
@require(
    lambda vehicle_subtype: vehicle_subtype in ALLOWED_SYBTYPES.values() if vehicle_subtype else True,
    "This vehicle_subtype is forbidden",
)
def check_vehicle_subtype(vehicle_subtype, **args):
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


@require(lambda year: 2016 <= year <= 2021)
@require(lambda downpayment: 0 <= downpayment < 0.5)
@require(lambda price: 1_000_000 <= price <= 20_000_000)
def check_numericals(year, downpayment, price, **args):
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
