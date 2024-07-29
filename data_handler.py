# data_handler.py

import pandas as pd
from influxdb_client import InfluxDBClient
from config import INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

def fetch_data(category, metric, period='-1h'):
    if category == 'api_request':
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {period})
          |> filter(fn: (r) => r["_measurement"] == "api_request")
          |> filter(fn: (r) => r["_field"] == "response_body")
          |> filter(fn: (r) => r["device_id"] == "{metric}")
          |> aggregateWindow(every: 1m, fn: last, createEmpty: false)
          |> yield(name: "last")
        '''
    else:
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {period})
          |> filter(fn: (r) => r["_measurement"] == "{category}")
          |> filter(fn: (r) => r["_field"] == "{metric}")
          |> aggregateWindow(every: 1m, fn: last, createEmpty: false)
          |> yield(name: "last")
        '''
    df = query_api.query_data_frame(query)
    if df.empty or '_value' not in df.columns:
        return pd.DataFrame(columns=['_time', '_value'])
    df['_value'] = pd.to_numeric(df['_value'], errors='coerce')
    df = df.dropna(subset=['_value'])
    return df[['_time', '_value']]
