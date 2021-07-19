import dask
from dask.distributed import Client
import sacred
import uuid
import os
import shutil
from ..helper import write_queued_experiments, upload_queue_to_s3, get_number_of_queued_experiments

RESOURCE_FOLDER_DIR = 'resources'

def do_local_storage(ex, folder_modifier=None):
    for obs in ex.observers:
        if type(obs)==sacred.observers.FileStorageObserver:
            return
    folder = 'data'
    if not folder_modifier is None:
        folder+=f'/{folder_modifier}'
    ex.observers.append(sacred.observers.FileStorageObserver(folder))

def do_s3_storage(ex, basedir_name, region='us-west-2', folder_modifier=None):
    for obs in ex.observers:
        if type(obs)==sacred.observers.S3Observer:
            return
    bucket = 'active-matter-simulations' 
    basedir = basedir_name 
    if not folder_modifier is None:
        basedir+=f'/{folder_modifier}'
        print(bucket)
    ex.observers.append(sacred.observers.S3Observer(bucket=bucket,
                                   basedir=basedir, region=region))

def run_all_dask_local_from_run_one(run_one, sim_list, n_tasks, **kwargs):
    lazy_results = []
    client = Client(threads_per_worker=1, n_workers = n_tasks)
    for sim in sim_list:
        lazy_results.append(dask.delayed(run_one)(sim, **kwargs))
    dask.compute(*lazy_results)

def get_simtype_from_simlist(sim_list):
    simtypes = set(d['SIMULATION_TYPE'] for d in sim_list)
    if len(simtypes)>1:
        raise RuntimeError("Currently, mixed simulation types are not supported!")
    return simtypes.pop()


def get_slurm_script(user, time, num_sims, sim_type = "", user_email=None):
    if user_email is None:
        user_email = user+"@caltech.edu"
    return f"""#!/bin/bash
#SBATCH --job-name="{sim_type} {user}"
#SBATCH --time={time}
#SBATCH --array=0-{num_sims-1}
#SBATCH --ntasks=1
#SBATCH --mail-type=ALL
#SBATCH --mail-user={user_email}
#SBATCH --output=out-%a.txt
#SBATCH --error=out-%a.txt
# ======START===============================
# module load ~/load-modules.sh
source ~/.bashrc
echo "------------------------------"
env
echo "------------------------------"
echo "The current job ID is $SLURM_JOB_ID"
echo "Running on $SLURM_JOB_NUM_NODES nodes: $SLURM_JOB_NODELIST"
echo "A total of $SLURM_NTASKS tasks is used"
CMD="python3 main.py"
echo $CMD
$CMD
# ======END================================= 
"""

def get_main_script_cluster(sim_type):
    if sim_type.lower() == 'SpringBox'.lower():
        run_one_line = "from IAMS.runners.SpringBoxRunner import run_one"
    elif sim_type.lower() == 'ANFDM'.lower():
        run_one_line = "from IAMS.runners.ANFDMRunner import run_one"
    else:
        raise RuntimeError(f"Unrecognized sim_type when calling get_main_script_cluster: {sim_type}")
    return f"""import os
from IAMS.helper import get_ith_simulation
{run_one_line}
slurm_task_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", "0"))
sim = get_ith_simulation(slurm_task_id, "queue.json")
run_one(sim)
"""

def generate_cluster_submission(sim_type, list_of_sims, username, time):
    ## Make sure we pass a sim_type we know exists
    assert(any([sim_type.lower()==defined_sim.lower() for defined_sim in ["SpringBox", "ANFDM"]]))
    ## Generate unique folder for submission
    uid = str(hex(hash(uuid.uuid4())))[2:]
    uid = f"{sim_type}-{uid}"
    slurm_str = get_slurm_script(username, time, num_sims=len(list_of_sims), sim_type=sim_type)
    main_script = get_main_script_cluster(sim_type)
    os.makedirs(uid)

    ## Write Queue file
    write_queued_experiments(list_of_sims, queue_file_location = f'{uid}/queue.json')

    ## Write submission file
    with open(f'{uid}/submit.sh', 'w') as f:
        f.write(slurm_str)

    ## Write main runner file
    with open(f'{uid}/main.py', 'w') as f:
        f.write(main_script)

    if os.path.exists(RESOURCE_FOLDER_DIR):
        print(f'Found resources in {RESOURCE_FOLDER_DIR}, adding them...')
        shutil.copytree(RESOURCE_FOLDER_DIR, f'{uid}/{RESOURCE_FOLDER_DIR}')
    else:
        print(f'Did not find any additional resources to be added to the cluster submission.')
    return uid

def upload_and_run_on_cluster(uid, username, run_on_scratch=True, scratch_loc = '/central/scratch'):
    ## Establish connection
    print('Establish connection...', end='')
    os.system(f"""ssh -nNf -o ControlMaster=yes -o ControlPath="./%L-%r@%h:%p" {username}@login.hpc.caltech.edu""")
    print('Done')

    if run_on_scratch:
        print('Generate Scratch...', end='')
        os.system(f"""ssh -o 'ControlPath=./%L-%r@%h:%p' {username}@login.hpc.caltech.edu mkdir -p {scratch_loc}/{username}""")
        os.system(f"""ssh -o 'ControlPath=./%L-%r@%h:%p' {username}@login.hpc.caltech.edu 'ln -sf {scratch_loc}/{username} ~/scratch'""")
        print('Done')
    ## Use connection
    print('Copy to cluster...', end='')
    file_loc = "~/"
    if run_on_scratch:
        file_loc+="scratch/"
    os.system(f"""rsync -e "ssh -o 'ControlPath=./%L-%r@%h:%p'" -azhru {uid} {username}@login.hpc.caltech.edu:{file_loc}""")
    print('Done')
    
    print("Submit job...", end='')
    os.system(f"""ssh -o 'ControlPath=./%L-%r@%h:%p' {username}@login.hpc.caltech.edu 'cd {file_loc}/{uid}/; sbatch submit.sh'""")
    print('Done')

    print('Close connection...', end='')
    os.system(f"""ssh -O exit -o ControlPath="./%L-%r@%h:%p" {username}@login.hpc.caltech.edu""")
    print('Done')

def upload_and_run_on_AWS(queue_name):
    print('Upload queue to S3...', end='')
    uid = upload_queue_to_s3(queue_name, RESOURCE_FOLDER_DIR)
    print('Done.')

    print(f'Submit job {uid}...', end='')
    import boto3
    client = boto3.client('batch')
    client.submit_job(
            jobName = uid,
            arrayProperties = {'size':get_number_of_queued_experiments(queue_name)},
            jobQueue = 'iams',
            jobDefinition = 'iams',
            containerOverrides = {'environment' : [{'name':'queue-fname' , 'value':uid}]}
            )
    print('Done.')
