from IAMS.helper import get_queued_experiments, upload_queue_to_s3, download_queue_from_s3
from IAMS.runners.runner_helper import upload_and_run_on_AWS
if __name__ == '__main__':
    upload_and_run_on_AWS('queue.json')
