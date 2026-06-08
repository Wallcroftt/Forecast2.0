import json
import pandas as pd
from typing import List, Dict, Optional
import boto3

s3_client = boto3.client("s3")

def get_latest_s3_file(bucket_name: str, prefix: str) -> Optional[str]:
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
    all_files = [obj for page in pages for obj in page.get("Contents", [])]
    if not all_files: return None
    latest = sorted(all_files, key=lambda x: x["LastModified"], reverse=True)[0]
    return latest["Key"]

def load_stations_from_s3(bucket_name: str, file_key: str) -> List[Dict]:
    content = s3_client.get_object(Bucket=bucket_name, Key=file_key)["Body"].read().decode("utf-8")
    data = []
    for line in content.splitlines():
        try: data.append(json.loads(line))
        except: continue
    return [s for entry in data if "_airbyte_data" in entry for s in entry["_airbyte_data"].get("stations", [])]