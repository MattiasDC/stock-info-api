import asyncio

from stock_market.core import OHLC, OHLCFetcher
from stock_market.core.ohlc import merge_ohlcs
from utils.logging import get_logger

logger = get_logger(__name__)


class RedisOHLCFetcher(OHLCFetcher):
    def __init__(self, redis, delegate):
        super().__init__("redis")
        self.redis = redis
        self.delegate = delegate

    async def fetch_from_cache(self, ticker):
        ohlc_json = await self.redis.get(ticker.symbol)
        return None if ohlc_json is None else OHLC.from_json(ohlc_json)

    async def fetch_single(self, start_date, end_date, ticker):
        ohlc = await self.fetch_from_cache(ticker)

        hit_or_miss = "hit"
        if ohlc is None or ohlc.start > start_date or ohlc.end < end_date:
            hit_or_miss = "miss"

            fetched_ohlc = await self.delegate.fetch_ohlc(
                [(start_date, end_date, ticker)]
            )
            if fetched_ohlc is None:
                return ticker, None
            assert len(fetched_ohlc) == 1

            ohlc = merge_ohlcs(ohlc, fetched_ohlc[0][1])

            # should we asyncio.create_task instead of await?
            await self.redis.set(ticker.symbol, ohlc.to_json())

        logger.debug(
            f"Cache {hit_or_miss}: ticker '{ticker}', start date '{start_date}', end"
            f" date '{end_date}'"
        )
        return ticker, ohlc

    async def fetch_ohlc(self, requests):
        tasks = []
        for request in requests:
            tasks.append(self.fetch_single(*request))
        return await asyncio.gather(*tasks)
