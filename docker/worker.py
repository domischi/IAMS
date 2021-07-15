import os
import uuid
from IAMS.helper import get_queued_experiments, get_ith_simulation, download_queue_from_s3
from IAMS.runners.runner_helper import RESOURCE_FOLDER_DIR
from datetime import date
if __name__ == '__main__':
    index = int(os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX", 0))
    uid = os.environ.get("queue-fname", "queue")
    queue_fname = uid+".json"
    download_queue_from_s3(uid, RESOURCE_FOLDER_DIR)
    sim = get_ith_simulation(index, queue_file_location=queue_fname)
    if sim.get('SIMULATION_TYPE').lower() == 'Springbox'.lower():
        from IAMS.runners.SpringBoxRunner import run_one
    elif sim.get('SIMULATION_TYPE').lower() == 'ANFDM'.lower():
        from IAMS.runners.ANFDMRunner import run_one
    else:
        raise RuneimeError(f"Unrecognized simuation_type: sim.get('SIMULATION_TYPE')...")
    run_one(sim, do_local=False, do_S3=True, folder_modifier=str(date.today())+'-'+str(index))
