import datetime as dt
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, constr
from stock_market.core import Ticker
from stock_market.ext.fetcher import YahooOHLCFetcher

from .config import get_settings
from .redis import init_redis_pool
from .redis_ohlc_fetcher import RedisOHLCFetcher

app = FastAPI(title="Stock Info API")


class TickerModel(BaseModel):
    symbol: constr(max_length=get_settings().max_ticker_symbol_length)

    def create(self):
        return Ticker(self.symbol)


class RequestModel(BaseModel):
    ticker: TickerModel
    start_date: dt.date
    end_date: dt.date


class RequestsModel(BaseModel):
    requests: List[RequestModel]


@app.on_event("startup")
async def startup_event():
    app.state.redis = init_redis_pool()


def create_fetcher(app):
    return RedisOHLCFetcher(app.state.redis, YahooOHLCFetcher())


@app.post("/ohlc")
async def ohlc(requests: RequestsModel):
    fetcher = create_fetcher(app)
    ohlc_results = await fetcher.fetch_ohlc(
        ((r.start_date, r.end_date, r.ticker.create()) for r in requests.requests)
    )
    # print(list(ohlc_results))
    return [(t.to_json(), o.to_json()) for t, o in ohlc_results]
