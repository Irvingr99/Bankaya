# -*- coding: utf-8 -*-
"""
Created on Thu Nov 16 16:09:11 2023

@author: Irving
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python_operator import PythonOperator
import json
import pandas as pd
from sqlalchemy import create_engine 



default_args = {
    'owner': 'bankaya',
    'depends_on_past': False,
    'start_date': datetime(2023, 11, 17),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'DAG_bankaya',
    default_args=default_args,
    description='Extracción, transformación y carga de datos',
    schedule_interval='0 0 * * *',  # Ejecución diaria a las 12 am
)

def extract_from_database(**kwargs):
    # Extrae datos de las tablas: Customer, Items, and Store
    # Suponiendo que las tablas se encuentran en una base de Postresql

    tasks = [
        PostgresOperator(
            task_id='extract_customer_data',
            postgres_conn_id='conn',
            sql="SELECT customer_id, customer_rfc FROM Customer",
            dag=dag
        ),
        PostgresOperator(
            task_id='extract_items_data',
            postgres_conn_id='conn',
            sql="SELECT item_id, item_name FROM Items",
            dag=dag
        ),
        PostgresOperator(
            task_id='extract_store_data',
            postgres_conn_id='conn',
            sql="SELECT store_id, store_name FROM Store",
            
            dag=dag
        ),
    ]

    return tasks

def extract_from_json(**kwargs):
    # Se extrae data del archivo JSON suponiendo que se encuentra en un bucket en S3 

    def extract_json_data():
        source_bucket = 'source_bucket'
        source_key = 'source_key.json'

        with open(f"/tmp/{source_key}", "r") as json_file:
            json_data = json.load(json_file)
            return json_data

    extract_json_task = PythonOperator(
        task_id='extract_json_data',
        python_callable=extract_json_data,
        provide_context=True, 
        dag=dag
    )

    return extract_json_task


# Función de transformación y carga de datos
def transform_and_load_data(**kwargs):
    # Obtener el resultado de la tarea de extracción del contexto
    ti = kwargs['ti']
    json_data = ti.xcom_pull(task_ids='extract_json_data')
    customer_data = ti.xcom_pull(task_ids='extract_customer_data')
    items_data = ti.xcom_pull(task_ids='extract_items_data')
    store_data = ti.xcom_pull(task_ids='extract_store_data')

    # Convertir resultados de las tareas de extracción en DataFrames
    df_customer = pd.DataFrame(customer_data)
    df_items = pd.DataFrame(items_data)
    df_store = pd.DataFrame(store_data)
    df_json = pd.DataFrame(json_data)

    # Transformaciones de datos
    
    # Transformación 1: customer_rfc
    df_customer['customer_rfc'] = df_customer['customer_rfc'].str.upper()
    # Transformación 2: item_name
    df_items['item_name'] = df_items['item_name'].str.upper()
    df_items['item_name'] = df_items['item_name'].replace('[^\w\s]', '', regex=True)
    # Transformación 3: item_quantity_bought
    df_json['item_quantity_bought'] = df_json.groupby('item_id')['quantity'].transform('sum')
    # Transformación 4: store_name
    df_store['store_name'] = df_store['store_name'].str.upper()
    df_store['store_name'] = df_store['store_name'].replace('[^\w\s]', '', regex=True)
    # Transformación 5: total_bought
    df_json['total_bought'] = df_json.groupby('item_id')['total_price'].transform('sum') * 20  # Tasa de conversión a pesos mexicanos
    # Transformación 6: purchase_date
    df_json['purchase_date'] = pd.to_datetime(df_json['creation_timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Mexico_City').dt.strftime('%Y-%m-%d')

   # Unir DataFrames
    df_combined = pd.merge(df_json, df_customer, how='left', on='customer_id')
    df_combined = pd.merge(df_combined, df_store, how='left', on='store_id')
    df_combined = pd.merge(df_combined, df_items, how='left', on='item_id')
    
    # Cargar datos en Redshift
    # Suponiendo que la tabla final se encuentra en Redshift
    engine = create_engine('redshift+psycopg2://user:password@host:port/database')
    df_combined.to_sql('big_table', engine, index=False, if_exists='replace')

# Tareas de extracción de datos
extract_database_task = extract_from_database()

# Tarea de extracción de datos del JSON
extract_json_task = extract_from_json()

# Tarea de transformación y carga de datos
transform_load_task = PythonOperator(
    task_id='transform_and_load_data',
    python_callable=transform_and_load_data,
    provide_context=True,
    dag=dag,
)
# Define el flujo de tareas
extract_database_task >> extract_json_task >> transform_load_task  # Define la dependencia entre las tareas

if __name__ == "__main__":
    dag.cli()
