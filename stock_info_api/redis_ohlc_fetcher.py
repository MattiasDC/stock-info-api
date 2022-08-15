import asyncio
import datetime as dt

import pandas as pd
from simputils.algos import inverse_ranges, rangify
from simputils.logging import get_logger
from stock_market.core import OHLC, OHLCFetcher
from stock_market.core.ohlc import merge_ohlcs

from .config import get_settings

logger = get_logger(__name__)


class RedisOHLCFetcher(OHLCFetcher):
    def __init__(self, redis, delegate):
        super().__init__("redis")
        self.redis = redis
        self.delegate = delegate

    async def __fetch_from_cache(self, ticker):
        ohlc_json = await self.redis.get(ticker.symbol)
        return None if ohlc_json is None else OHLC.from_json(ohlc_json)

    async def __handle_miss(self, start_date, end_date, ticker, ohlc):
        fetched_ohlc = await self.delegate.fetch_ohlc(
            [
                (
                    start_date - dt.timedelta(days=30),
                    end_date + dt.timedelta(days=30),
                    ticker,
                )
            ]
        )

        if fetched_ohlc is None or fetched_ohlc[0][1] is None:
            logger.warning(
                f"Could not fetch ohlc data for: {ticker}, {start_date}, {end_date}"
            )
            return None
        assert len(fetched_ohlc) == 1

        ohlc = merge_ohlcs(ohlc, fetched_ohlc[0][1])
        # should we use asyncio.create_task instead of await?
        await self.redis.set(ticker.symbol, ohlc.to_json())

        return ohlc

    async def fetch_single(self, start_date, end_date, ticker):
        assert start_date <= end_date
        if start_date == end_date:
            return ticker, None

        ohlc = await self.__fetch_from_cache(ticker)

        cache_hit = True

        if ohlc is None:
            cache_hit = False
            ohlc = await self.__handle_miss(start_date, end_date, ticker, None)

        if ohlc is None:
            return ticker, None

        trimmed_ohlc = ohlc.trim(start_date, end_date) if ohlc is not None else None
        if trimmed_ohlc is None:
            ohlc = await self.__handle_miss(start_date, end_date, ticker, None)
        else:
            missing_dates = pd.date_range(start_date, end_date).difference(
                trimmed_ohlc.dates
            )
            first_date = missing_dates[0].date()
            days_between_first_date = list(
                map(lambda d: d.days, list(missing_dates.date - first_date))
            )
            max_days_between_two_days = max(
                map(len, inverse_ranges(rangify(days_between_first_date))), default=0
            )

            if (
                trimmed_ohlc.start > start_date
                or trimmed_ohlc.end < end_date
                or max_days_between_two_days
                > get_settings().max_days_between_ticker_data_cache
            ):
                ohlc = await self.__handle_miss(start_date, end_date, ticker, ohlc)

        hit_or_miss = "hit" if cache_hit else "miss"
        logger.debug(f"Cache {hit_or_miss}: {ticker}, {start_date}, {end_date}")
        return ticker, ohlc.trim(start_date, end_date)

    async def fetch_ohlc(self, requests):
        tasks = []
        for request in requests:
            tasks.append(self.fetch_single(*request))
        return await asyncio.gather(*tasks)
