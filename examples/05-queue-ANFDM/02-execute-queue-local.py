from IAMS.helper import get_queued_experiments
from IAMS.runners.ANFDMRunner import run_all_dask_local_from_json
if __name__ == '__main__':
    sim_parameters = get_queued_experiments()
    run_all_dask_local_from_json(n_tasks=2)
