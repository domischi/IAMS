import os
import uuid
from IAMS.helper import get_queued_experiments, get_ith_simulation, download_queue_from_s3
from IAMS.runners.SpringBoxRunner import run_one
from datetime import date
if __name__ == '__main__':
    index = int(os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX", 0))
    queue_fname = os.environ.get("queue-fname", "queue.json")
    download_queue_from_s3(queue_fname)
    sim = get_ith_simulation(index)
    run_one(sim, do_local=False, do_S3=True, folder_modifier=str(date.today())+'-'+str(index))
