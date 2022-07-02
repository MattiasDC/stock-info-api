import datetime as dt
from http import HTTPStatus
from typing import List

from fastapi import FastAPI, Response
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
    if ohlc_results is None:
        return Response(status_code=HTTPStatus.NO_CONTENT.value)

    json_results = [
        (t.to_json(), o.to_json()) for t, o in ohlc_results if o is not None
    ]
    if len(json_results) == 0:
        return Response(status_code=HTTPStatus.NO_CONTENT.value)

    return json_results
