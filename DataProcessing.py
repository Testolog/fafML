# Databricks notebook source
from dataclasses import dataclass
from typing import List, Dict

from pyspark.sql.functions import *
from pyspark.sql import DataFrame, Window


def total_summarize(df: DataFrame) -> DataFrame:
    common_window = Window.partitionBy("namePeriod", "YEAR_ID")
    return df \
        .withColumn("periodId", generate_id_agreement([7, 14, 30, 180, 365], "dayFromMinimum")) \
        .withColumn("namePeriod", generate_number_dates([7, 14, 30, 180, 365], "dayFromMinimum")) \
        .select(col("YEAR_ID"),
                col("periodId"),
                col("namePeriod"),
                first("DEALSIZE").over(common_window.orderBy(col("sales").desc())).alias("bestDealSize"),
                first("productline").over(common_window.orderBy(col("sales").desc())).alias("bestProductLineBySales"),
                max("sales").over(Window.partitionBy("productline", "namePeriod", "YEAR_ID")).alias(
                    "maximumSalesPerProductLine"),
                sum("sales").over(common_window).alias("sumPerPeriod"),
                first("productcode").over(common_window.orderBy(col("sales").desc())).alias("bestProduct"),
                row_number().over(Window.partitionBy("YEAR_ID", "namePeriod").orderBy("namePeriod")).alias("rnumb")) \
        .where(col("rnumb") == 1)


def pivot_catogaries(df: DataFrame) -> DataFrame:
    return df \
        .withColumn("namePeriod", generate_number_dates([7, 14, 30, 180, 365], "dayFromMinimum")) \
        .groupBy("YEAR_ID", "namePeriod") \
        .pivot("productline") \
        .agg(max("sales").alias("maxSales"), avg("sales").alias("avgSales"), min("sales").alias("minSales"),
             count("*").alias("count"))


@dataclass(frozen=True)
class JobConfig(object):
    file_system_name_input: str
    storage_account_name_input: str
    options: Dict[str, str]


def generate_number_dates(ll: List[int], name: str):
    def _generate(_col, index):
        if index < len(ll) - 1:
            return _col.otherwise(_generate(when(col(name) <= ll[index], ll[index]), index + 1))
        else:
            return _col.otherwise(when(col(name) <= ll[index], ll[index]))

    return _generate(when(col(name) <= ll[0], ll[0]), 1)


def generate_id_agreement(ll: List[int], name: str):
    return concat_ws("", array([when(col(name) <= elm, 1).otherwise(0) for elm in ll]))


def update_mounting(path_to: str, update: bool, dbutils, config: JobConfig) -> None:
    if update:
        dbutils.fs.unmount(path_to)

    dbutils.fs.mount(
        source="abfss://{0}@{1}.dfs.core.windows.net".format(config.file_system_name_input,
                                                             config.storage_account_name_input),
        mount_point=path_to,
        extra_configs=config.options)


# COMMAND ----------

application_id = "37868468-dcf3-4893-84f6-88243d3ecd39"
directory_id = "1c33c3bb-76a0-45ac-b396-1f584a6210fe"
password = "_9SL-5fzwwQ-JzGZ3w.qm0k2T14GGD01fK"

configs = {"fs.azure.account.auth.type": "OAuth",
           "fs.azure.account.oauth.provider.type": "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
           "fs.azure.account.oauth2.client.id": application_id,
           "fs.azure.account.oauth2.client.secret": password,
           "fs.azure.account.oauth2.client.endpoint": "https://login.microsoftonline.com/{0}/oauth2/token".format(
               directory_id)}
rawPath = "/mnt/raw"
stagePath = "/mnt/stage"

# dbutils.fs.mount(
#     source="abfss://{0}@{1}.dfs.core.windows.net".format("raw", "fordatalocality"),
#     mount_point=rawPath,
#     extra_configs=configs)
display(spark.read.option("header", "true") \
    .option("dateFormat", "MM/dd/yyyy") \
    .options(**configs) \
    .csv("abfss://{0}@{1}.dfs.core.windows.net".format("raw", "fordatalocality")))
# dbutils.fs.mount(
#     source="abfss://{0}@{1}.dfs.core.windows.net".format("raw", "fordatalocality"),
#     mount_point=rawPath,
#     extra_configs=configs)

# for_input = JobConfig(getArgument("storageName"), getArgument("inputContainer"), configs)
# for_output = JobConfig(getArgument("storageName"), getArgument("inputContainer"), configs)
# df = spark.read \
#     .option("header", "true") \
#     .option("dateFormat", "MM/dd/yyyy") \
#     .csv(path.join(rawPath, "sales_data_sample.csv")) \
#     .select(to_date('orderdate', "MM/dd/yyyy").alias("orderdate"),
#             col('ordernumber').cast("double"),
#             col('quantityordered').cast("double"),
#             col('sales').cast("double"),
#             col("YEAR_ID").cast("int").alias("YEAR_ID"),
#             col("DEALSIZE"),
#             'productline',
#             'qtr_id',
#             'msrp',
#             'productcode') \
#     .withColumn("dayFromMinimum",
#                 datediff(col("orderDate"), first(col("orderDate"))
#                          .over(Window.partitionBy(col("YEAR_ID")).orderBy(col("orderDate")))))

# total_summarize(df).write.mode("overwrite").option("header", "true").csv(path.join(stagePath, "totalSumerize"))
# display(pivot_catogaries(df))

# COMMAND ----------

# MAGIC %fs unmount /mnt/raw

# COMMAND ----------

# MAGIC %sh ps aux