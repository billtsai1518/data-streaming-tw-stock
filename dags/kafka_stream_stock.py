import uuid
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'yktsai',
    'start_date': datetime(2024, 1, 1, 14, 00)
}

def get_data():
    import requests

    res = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL")
    res = res.json()

    return res


def stream_data():
    import json
    from kafka import KafkaProducer
    import logging

    producer = KafkaProducer(bootstrap_servers=['broker:29092'], max_block_ms=5000)

    try:
        res = get_data()
     
        for i, r in enumerate(res):
            data = {}
            data['id'] = str(uuid.uuid4())
            data['code'] = r['Code']
            data['name'] = r['Name']
            data['trade_volume'] = r['TradeVolume']
            data['trade_value'] = r['TradeValue']
            data['opening_price'] = r['OpeningPrice']
            data['highest_price'] = r['HighestPrice']
            data['lowest_price'] = r['LowestPrice']
            data['closing_price'] = r['ClosingPrice']
            data['change'] = r['Change']
            data['transaction'] = r['Transaction']
            data['created_at'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            producer.send('tw_stock_day_all', json.dumps(data).encode('utf-8'))

    except Exception as e:
        logging.error(f'An error occured: {e}')

with DAG('tw_stock_task',
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False) as dag:

    streaming_task = PythonOperator(
        task_id='stream_data_from_twse',
        python_callable=stream_data
    )
