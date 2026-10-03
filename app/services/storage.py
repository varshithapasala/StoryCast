from abc import ABC, abstractmethod
from pathlib import Path
from app.core.config import get_settings

class Storage(ABC):
    @abstractmethod
    def put(self,local:Path,key:str)->str: ...

class LocalStorage(Storage):
    def __init__(self): self.root=get_settings().storage_root
    def put(self,local,key): return str(local)

class S3Storage(Storage):
    def __init__(self):
        import boto3
        s=get_settings(); self.bucket=s.s3_bucket
        if not self.bucket:
            raise RuntimeError("S3_BUCKET is required when STORAGE_PROVIDER=s3")
        if bool(s.s3_access_key_id) != bool(s.s3_secret_access_key):
            raise RuntimeError("Set both S3 access-key values or leave both empty to use the AWS credential chain")
        options={}
        if s.s3_endpoint_url: options["endpoint_url"]=s.s3_endpoint_url
        if s.aws_region: options["region_name"]=s.aws_region
        if s.s3_access_key_id:
            options["aws_access_key_id"]=s.s3_access_key_id
            options["aws_secret_access_key"]=s.s3_secret_access_key
        self.client=boto3.client("s3",**options)
    def put(self,local,key): self.client.upload_file(str(local),self.bucket,key); return f"s3://{self.bucket}/{key}"

def storage_provider(): return S3Storage() if get_settings().storage_provider=="s3" else LocalStorage()
