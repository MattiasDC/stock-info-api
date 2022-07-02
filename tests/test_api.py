import datetime as dt

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient
from stock_market.core import OHLC, Ticker

from stock_info_api.main import app


def get_client_impl():
    with TestClient(app) as client:
        app.state.redis = FakeRedis()
        while True:
            yield client


@pytest.fixture
def client():
    return next(get_client_impl())


@pytest.fixture
def spy():
    return Ticker("SPY")


@pytest.fixture
def start_date():
    return dt.date(2021, 1, 4)


@pytest.fixture
def end_date():
    return dt.date(2021, 1, 6)


def test_api(client, spy, start_date, end_date):
    response = client.post(
        "/ohlc",
        json={
            "requests": [
                {
                    "ticker": {"symbol": spy.symbol},
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                }
            ]
        },
    )
    json_result = response.json()
    assert len(json_result) == 1
    ticker_json, ohlc_json = response.json()[0]
    ticker = Ticker.from_json(ticker_json)
    ohlc = OHLC.from_json(ohlc_json)

    assert ticker == spy
    assert ohlc.start == start_date
    assert ohlc.end == end_date - dt.timedelta(days=1)
