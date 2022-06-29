FROM python:3.10-slim-buster

RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && apt-get purge -y --auto-remove 

RUN mkdir -p /app

# set working directory
WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip

COPY pyproject.toml .
COPY setup.cfg .

COPY ./stock_info_api ./stock_info_api

RUN pip install -e . --no-cache-dir

EXPOSE 8000
CMD ["uvicorn", "stock_info_api.main:app", "--host", "0.0.0.0", "--lifespan=on", "--use-colors", "--reload"]