# meteoblue Python Dataset SDK

[![PyPI version](https://badge.fury.io/py/meteoblue-dataset-sdk.svg)](https://badge.fury.io/py/meteoblue-dataset-sdk)

This library simplifies access to the [meteoblue dataset API](https://docs.meteoblue.com/en/apis/environmental-data/dataset-api).

WARNING: This library is under development and has no declared stable version 1.0 yet! Use with caution!

In order to use this library you need a meteoblue API key.

Features:
- Fetch any dataset from the meteoblue environmental data archive
- Transparently integrates job queues to query large datasets
- Efficiently transfers data using compressed protobuf messages
- Asynchronous interface to query data in parallel
- Data can be used as simple floating-point arrays. No further formatting required.


## Installation
- Ensure that you are using at least Python 3.7 with `python --version` (Sometimes `python3`)
- Install the module with `pip install 'meteoblue_dataset_sdk >=0.0,<0.1'` (Sometimes `pip3`)

This module will also install the following dependencies automatically:
- aiohttp >=3.6,<4
- protobuf >=3.0,<4


## Usage
See [main.py](./main.py) for a working example. To generate the query JSON it is highly recommended to use the [dataset API web interfaces](https://docs.meteoblue.com/en/apis/environmental-data/web-interfaces).

```python
import meteoblue_dataset_sdk
import logging

# Display information about the current download state
logging.basicConfig(level=logging.INFO)

query = {
    "units": {
        "temperature": "C",
        "velocity": "km/h",
        "length": "metric",
        "energy": "watts",
    },
    "geometry": {
        "type": "MultiPoint",
        "coordinates": [[7.57327, 47.558399, 279]],
        "locationNames": ["Basel"],
    },
    "format": "json",
    "timeIntervals": ["2019-01-01T+00:00/2019-01-01T+00:00"],
    "timeIntervalsAlignment": "none",
    "queries": [
        {
            "domain": "NEMSGLOBAL",
            "gapFillDomain": None,
            "timeResolution": "hourly",
            "codes": [{"code": 11, "level": "2 m above gnd"}],
        }
    ],
}
client = meteoblue_dataset_sdk.Client(apikey="xxxxxx")
result = client.querySync(query)
# result is a structured object containing timestamps and data

timeInterval = result.geometries[0].timeIntervals[0]
data = result.geometries[0].codes[0].timeIntervals[0].data

print(timeInterval)
# start: 1546300800
# end: 1546387200
# stride: 3600
```

NOTE: `timeInterval.end` is the first timestamp that is not included anymore in the time interval.

If your code is using `async/await`, you should use `await client.query()` instead of `client.querySync()`. Asynchronous IO is essential for modern webserver frameworks like Flask or FastAPI.

```python
client = meteoblue_dataset_sdk.Client(apikey="xxxxxx")
result = await client.query(query)
```

More detailed output of the `result` object. The output is defined as [this protobuf structure](./meteoblue_dataset_sdk/Dataset.proto).

```
geometries {
  domain: "NEMSGLOBAL"
  lats: 47.66651916503906
  lons: 7.5
  asls: 499.7736511230469
  locationNames: "Basel"
  nx: 1
  ny: 1
  timeResolution: "hourly"
  timeIntervals {
    start: 1546300800
    end: 1546387200
    stride: 3600
  }
  codes {
    code: 11
    level: "2 m above gnd"
    unit: "\302\260C"
    aggregation: "none"
    timeIntervals {
      data: 2.890000104904175
      data: 2.690000057220459
      data: 2.549999952316284
      data: 2.380000114440918
      data: 2.2699999809265137
      data: 2.119999885559082
      data: 1.9900000095367432
      data: 1.8300000429153442
      data: 1.8200000524520874
      data: 2.0999999046325684
      data: 2.430000066757202
      data: 2.9200000762939453
      data: 3.7200000286102295
      data: 3.930000066757202
      data: 3.9100000858306885
      data: 3.5299999713897705
      data: 3.130000114440918
      data: 2.880000114440918
      data: 2.6500000953674316
      data: 2.4600000381469727
      data: 2.2799999713897705
      data: 2.0299999713897705
      data: 1.690000057220459
      data: 1.3799999952316284
    }
  }
}
```


## Developer setup
```bash
python3 -m venv env
source env/bin/activate
pip3 install -r requirements.txt
```