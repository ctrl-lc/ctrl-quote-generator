from typing import Literal
from fastapi import FastAPI, Response, status
from numpy_financial import pmt


app = FastAPI()


@app.get("/")
def get_quote(response: Response,
              vehicle_type: Literal['semitruck', 'semitrailer'],
              year: int,
              price: int,
              VAT_included: bool,
              downpayment: float = 0,
              truck_brand: Literal['KAMAZ', 'MAZ', 'MAN', 'DAF',
                                   'MERCEDES', 'VOLVO', 'SCANIA',
                                   'RENAULT', 'IVECO'] = None,
              trailer_brand: Literal['SCHMITZ', 'KOGEL', 'NEFAZ',
                                     'MAZ'] = None,
):

    if not 0 <= downpayment < 0.5:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return "`downpayment` should be > 0 and < 0.5"

    if vehicle_type == 'semitruck' and truck_brand is None:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return "`truck_brand` should be given"

    if vehicle_type == 'semitrailer' and trailer_brand is None:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return "`trailer_brand` should be given"

    if not 2016 <= year <= 2021:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return "`year` should be >= 2016 and <= 2020"

    if vehicle_type == 'semitruck' and truck_brand in ['KAMAZ', 'MAZ'] \
            and not 2018 <= year <= 2021:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return 'For truck brands "KAMAZ" and "MAZ" `year` should be >= 2016 and <= 2020'

    return calc_payment(price, downpayment, VAT_included)


def calc_payment(price: int, downpayment: float, VAT_included: bool) -> int:
    BASE_RATE = 0.13
    VAT_RATE = 0.2
    PERIODS = 48

    nim = 0.1 if downpayment < 0.1 else 0.07

    rate = (BASE_RATE + nim) * (1 + VAT_RATE)

    price_plus_VAT = price if VAT_included else price * (1 + VAT_RATE)

    return -pmt(rate/12, PERIODS, price_plus_VAT)