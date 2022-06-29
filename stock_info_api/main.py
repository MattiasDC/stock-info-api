import datetime as dt
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, constr
from stock_market.core import Ticker

from .config import get_settings
from .redis import init_redis_pool

app = FastAPI(title="Stock Info API")


class TickerModel(BaseModel):
    symbol: constr(max_length=get_settings().max_ticker_symbol_length)

    def create(self):
        return Ticker(self.symbol)


class TickersModel(BaseModel):
    tickers: List[TickerModel]


@app.on_event("startup")
async def startup_event():
    app.state.redis = init_redis_pool()


@app.post("/ohlc")
def ohlc(start_date: dt.date, end_date: dt.date, tickers: TickersModel):
    print([start_date, end_date, tickers], flush=True)
