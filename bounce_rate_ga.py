# Databricks notebook source

# COMMAND ----------
import boto3
import json
import os
import requests

from datetime import datetime
from datetime import timedelta
from pyspark.sql import DataFrame
from pyspark.sql.functions import col
from pyspark.sql.functions import concat
from pyspark.sql.functions import count
from pyspark.sql.functions import countDistinct
from pyspark.sql.functions import date_format
from pyspark.sql.functions import lit
from pyspark.sql.functions import lower
from pyspark.sql.functions import sum
from pyspark.sql.functions import to_date
from pyspark.sql.functions import when
from pyspark.sql.functions import expr
from pyspark.sql.types import LongType
from pyspark.sql.types import StringType
from pyspark.sql.types import StructField
from pyspark.sql.types import StructType
from pyspark.sql.types import IntegerType


# COMMAND ----------
NOW = datetime.now() - timedelta(hours=3)
DATA = NOW.date()
AIRFLOW_ENVIRONMENT = os.getenv("AIRFLOW_ENVIRONMENT")
DATABRICKS_HOME = os.getenv("DATABRICKS_HOME", ".")
DAG_ID = json.loads(os.getenv("METADATA_DAG", "{}"))["dag_id"]
PAYLOAD_PATH = os.path.join(DATABRICKS_HOME, DAG_ID,"assets","setup_file","bounce_rate_ga.json")
S3_SERVING = os.getenv('S3_SERVING')
S3_SAVING_PATH = os.path.join(f"s3://{S3_SERVING}/{DAG_ID}",f"{NOW.year}/{NOW.month}/{NOW.day}")
UPSERT_QUEUE = os.getenv("UPSERT_QUEUE") 

# COMMAND ----------
def main()-> None:
    """
    Calls the function that evaluates what the execution period is, in this case, what day inside the bucket it will process, group and send to redshift.
    Parameters: None  
    Returns: None   
    """
    ssm_parameters = get_parameters_from_aws_ssm(f'airflow_{DAG_ID}', return_value='parameters_from_ssm')   
    df_raw = extract(parameters_dag=ssm_parameters)
    df_modeled = transform(df_raw)
    load(df_modeled)
    
# COMMAND ----------
def get_parameters_from_aws_ssm(parameter_name: str, return_value: str = 'response') -> dict:
    """
    Calls the function that gets the parameters of the AWS SSM parameter store. this return of parameter is stored in a variable. 
    
    Parameters: 
    parameter_name -> string: name of parameter.    
    return_value -> string: which option you want the function to return.  
    Returns: The dict containing the extracted parameter with method and days_proc.    
    """
    AWS_SESSION = boto3.Session()
    client = AWS_SESSION.client(service_name="ssm", region_name="us-east-2")
    
    try:
        response = client.get_parameter(Name=parameter_name)
        if return_value == 'parameters_from_ssm':
            ssm_parameters_dag = response.get("Parameter").get("Value")
            parameters_from_ssm = json.loads(ssm_parameters_dag) 
            print(f"LOG - PARÂMETROS CARREGADOS COM SUCESSO!")
            return parameters_from_ssm
        else:
            return response.get("Parameter", {}).get("Value", None)
    except Exception as e:
        print(f"LOG - ERRO AO CONSULTAR O PARÂMETRO {parameter_name}: {e}")
        return None

# COMMAND ----------
def extract(parameters_dag: dict) -> DataFrame:
    """
    Calls the function of Extract of data from AWS S3 bucket by using the method and dates passed by parameter. is used one Parameter! one  dict containing the extracted parameter with days for reproc. This function Returns one DataFrame containingS the extracted data from S3.
    
    Parameters: parameters_dag -> dict: the method and dates passed by parameter 
    Returns: df->DataFrame: One DataFrame containing the extracted data from AWS S3 bucket s3://mm-lakehouse-landing-layer/gcp_extraction/analytics_outbound/YEAR/MONTH/DAY
    """     
    global DATA
    try:
        custom_schema = StructType([
            StructField("date", StringType(), True),
            StructField("device", StructType([
                StructField("deviceCategory", StringType(), True),
            ]), True),
            StructField("fullvisitorid", StringType(), True),
            StructField("visitstarttime", LongType(), True),
            StructField("totals", StructType([
                StructField("pageviews", LongType(), True),
                StructField("newVisits", LongType(), True),
                StructField("bounces", LongType(), True),
                StructField("visits", LongType(), True),
                StructField("transactions", LongType(), True),
            ]), True),
            StructField("clientId", StringType(), True)
        ])
        df = spark.read.format('parquet').schema(custom_schema).load(f"{parameters_dag['extract_url']}/{DATA.year}/{DATA.month:02d}/{DATA.day:02d}/")
        print(f"LOG - Existe dados no bucket para o dia {DATA}! Foi realizada a leitura desse arquivo!")
        return df

    except:
        print(f"LOG - Não existe dados no bucket para o dia {DATA}! Será feito uma tentativa subtraindo -1 no dia.")
        DATA = DATA - timedelta(days=int(parameters_dag['days_proc']))
        return extract(parameters_dag)

# COMMAND ----------
def transform (df: DataFrame)-> DataFrame:
    """
    Calls the function of transformation the dataframe, final objective of this transformation are the grouped daily metrics. Then, after having the analytical DF, we do the necessary groupings and transform them to the necessary columns. by changing the type of the columns to int, float and string and adding a new column. The Parameters used is the Dataframe to be transformed. Return the  Transformed dataframe
     
    Parameters:df -> DataFrame: DataFrame containing the extracted data from Redshift
    Returns: df -> DataFrame: Return the Transformed dataframe
    """      
    dict_transformations = {
        "device.deviceCategory": "lower(device.deviceCategory)",
        "totals.pageviews": "lower(totals.pageviews)",
        "totals.newVisits": "lower(totals.newvisits)",
        "totals.bounces": "lower(totals.bounces)",
        "totals.visits": "lower(totals.visits)",
        "totals.transactions": "lower(totals.transactions)"}

    for columns, expr_str in dict_transformations.items():
        df = df.withColumn(columns.replace(".", "_"), expr(expr_str))

    df = df.filter(col("totals_visits") == 1). \
        groupBy("date", "device_deviceCategory").agg(
        countDistinct(concat(col("fullvisitorid"), col("visitstarttime").cast(StringType()))).cast(IntegerType()).alias("quantidade_sessoes"),
        sum(col("totals_pageviews")).cast(IntegerType()).alias("quantidade_pageviews"),
        countDistinct("clientId").cast(IntegerType()).alias("quantidade_visitantes_unicos"),
        count(when(col("totals_newVisits") == 1, 1)).cast(IntegerType()).alias("quantidade_novos_visitantes"),
        count(when(col("totals_newVisits").isNull(), 1)).cast(IntegerType()).alias("quantidade_antigos_visitantes"),
        countDistinct(when(col("totals_bounces") == 1, concat(col("fullvisitorid"), col("visitstarttime").cast(StringType())))).cast(IntegerType()).alias("quantidade_bounces"),
        countDistinct(when(col("totals_pageviews") == 1, concat(col("fullvisitorid"), col("visitstarttime").cast(StringType())))).cast(IntegerType()).alias("quantidade_soft_bounces"),
        sum(col("totals_transactions")).cast(IntegerType()).alias("quantidade_transacoes"))

    rename_columns_dict = {'date': 'pk_data_evento', 
                           'device_deviceCategory': 'pk_categoria_dispositivo'}
    df = df.select([col(c).alias(rename_columns_dict.get(c, c)) for c in df.columns]).sort(col("pk_data_evento"),col("pk_categoria_dispositivo"))
    df = df.withColumn("pk_data_evento", to_date(col("pk_data_evento"), "yyyyMMdd")).withColumn("pk_data_evento", date_format(col("pk_data_evento"), "yyyy-MM-dd"))
    df = df.withColumn('data_processamento', lit(NOW.strftime("%Y-%m-%d %H:%M:%S")))
    print('LOG - Dados Transformados e Agrupados com Sucesso!')
    del dict_transformations
    del rename_columns_dict
    return df

# COMMAND ----------
def save_on_s3(df: DataFrame) -> None:
    """
    Calls the function of write of dataframe the in S3.
    
    Parameters: df -> dataframe: the dataframe to write
    Returns -> string: confirmation message indicating the number of rows written
    """
    df.repartition(1) \
        .write \
        .mode('overwrite') \
        .format('avro') \
        .save(S3_SAVING_PATH)
    print(f"- DF gravado no formato avro no caminho: {S3_SAVING_PATH}")
    return S3_SAVING_PATH 

# COMMAND ----------
def send_upsert() -> None:
    """
    Calls the function of load the dataframe, sends an upsert of request to the specified API endpoint.
    
    Parameters: None
    Returns: None
    """
    with open(PAYLOAD_PATH, "r") as file:
        payload = json.load(file)
    
    payload["queue_name"] = UPSERT_QUEUE
    payload["s3_path"] = S3_SAVING_PATH

    upsert_environment = "prod" if "production" in AIRFLOW_ENVIRONMENT else "dev"
    upsert_url = get_parameters_from_aws_ssm(f"upsert_redshift_api_{upsert_environment}")
    headers = {"Content-Type": "application/json"}

    response = requests.request(
        method="PUT",
        url=upsert_url,
        headers=headers,
        data=json.dumps(payload)) 

    print(f"Response API UPSERT")
    print(f"Status Code: {response.status_code}")
    print(f"Reason: {response.reason}")
    print(f"Response: {response.text}")
    response.raise_for_status()

# COMMAND ----------
def load(df: DataFrame) -> dict:
    """
    Calls the function of load the dataframe. 

    Parameters: df -> DataFrame: DataFrame containing the extracted data from S3
    Returns: response -> Dict: One dictionary with: message,tasks,arn.
    """
    save_on_s3(df)
    response = send_upsert()
    print('LOG - Processo de LOAD finalizado com sucesso.')
    return response

# COMMAND ----------
if __name__ == '__main__':
    main()