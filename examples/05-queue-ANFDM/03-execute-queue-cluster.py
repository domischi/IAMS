from IAMS.helper import get_queued_experiments
from IAMS.runners.runner_helper import generate_cluster_submission, upload_and_run_on_cluster
import shutil
if __name__ == '__main__':
    sim_parameters = get_queued_experiments()
    u = generate_cluster_submission("ANFDM", sim_parameters, "dominiks", "0-00:20:00")
    upload_and_run_on_cluster(u, "dominiks")
    shutil.rmtree(u)
