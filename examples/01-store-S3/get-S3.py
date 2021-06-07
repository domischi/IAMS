import boto3
import os
from pprint import pprint

s3_resource = boto3.resource('s3')
bucket = s3_resource.Bucket('active-matter-simulations')

newest_run = [s.get('Prefix') for s in bucket.meta.client.list_objects(Bucket=bucket.name, Prefix='simple-storage/', Delimiter='/').get('CommonPrefixes')]
newest_run = sorted(newest_run, key=lambda s: int(s[:-1].split('/')[-1]))[-1]

for obj in bucket.objects.filter(Prefix = newest_run):
    if not os.path.exists(os.path.dirname(obj.key)):
        os.makedirs(os.path.dirname(obj.key))
    bucket.download_file(obj.key, obj.key) # save to same path
