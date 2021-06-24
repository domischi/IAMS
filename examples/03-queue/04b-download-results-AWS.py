import os
import boto3
import datetime

if __name__ == '__main__':
    sim_day = str(datetime.date.today())
    client = boto3.resource('s3')
    bucket = client.Bucket('active-matter-simulations')
    for obj in bucket.objects.filter(Prefix = f'SpringBox/{sim_day}'):
        if not os.path.exists(os.path.dirname(obj.key)):
            os.makedirs(os.path.dirname(obj.key))
        bucket.download_file(obj.key, obj.key)
