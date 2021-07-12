import os
import uuid
from IAMS.helper import get_queued_experiments, get_ith_simulation
from IAMS.runners.SpringBoxRunner import run_all_dask_local_from_json, run_one
from datetime import date
if __name__ == '__main__':
    sim_parameters = get_queued_experiments()
    run_all_dask_local_from_json(n_tasks=1)
    #index=0
    #sim = get_ith_simulation(index, queue_file_location='queue.json')
    #run_one(sim, do_local=False, do_S3=True, folder_modifier = 'loc'+str(date.today())+'-'+str(index))
