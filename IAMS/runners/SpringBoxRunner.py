import os
import datetime
import uuid
from copy import deepcopy
import numpy as np
from tqdm import tqdm
import sacred
import numba
import warnings
warnings.simplefilter('ignore', category=numba.NumbaWarning)
import IAMS.simulators.SpringBox.SpringBox as SB
from IAMS.simulators.SpringBox.SpringBox.integrator import integrate_one_timestep
from IAMS.simulators.SpringBox.SpringBox.activation import activation_fn_dispatcher
from IAMS.simulators.SpringBox.SpringBox.post_run_hooks import post_run_hooks
from IAMS.simulators.SpringBox.SpringBox.measurements import do_measurements, do_one_timestep_correlation_measurement
import dask
from dask.distributed import Client
import uuid

ex = sacred.Experiment()
#ex.observers.append(sacred.observers.FileStorageObserver('data'))
#ex.observers.append(sacred.observers.S3Observer(bucket='active-matter-simulations',
#                               basedir='SpringBox'))
ex.dependencies.add(sacred.dependencies.PackageDependency("SpringBox",SB.__version__))

def do_local_storage(folder_modifier=None):
    for obs in ex.observers:
        if type(obs)==sacred.observers.FileStorageObserver:
            return
    folder = 'data'
    if not folder_modifier is None:
        folder+=f'.{folder_modifier}'
    ex.observers.append(sacred.observers.FileStorageObserver(folder))

def do_s3_storage(region='us-west-2', folder_modifier=None):
    for obs in ex.observers:
        if type(obs)==sacred.observers.S3Observer:
            return
    bucket = 'iams' 
    if not folder_modifier is None:
        bucket+=f'/{folder_modifier}'
        print(bucket)
    ex.observers.append(sacred.observers.S3Observer(bucket=bucket,
                                   basedir='SpringBox', region=region))

@ex.config
def cfg():
    ## These are only default values that can be overwritten by the caller
    run_id = 0
    sweep_experiment=False
    m_init = 1.
    spring_k = 1.
    spring_lower_cutoff = 0.001
    spring_r0 = 0.
    Rdrag = 0.
    drag_factor = 1.

def get_sim_info(old_sim_info, _config, i):
    sim_info = old_sim_info
    dt = _config['dt']
    L = _config['L']
    T = _config['T']
    vx = _config.get('window_velocity', [0,0])[0]
    vy = _config.get('window_velocity', [0,0])[1]
    savefreq_fig = _config['savefreq_fig']
    savefreq_dd = _config['savefreq_data_dump']
    sim_info['t']     = i*dt
    sim_info['time_step_index'] = i
    sim_info['x_min'] = -L+dt*vx*i
    sim_info['y_min'] = -L+dt*vy*i
    sim_info['x_max'] =  L+dt*vx*i
    sim_info['y_max'] =  L+dt*vy*i
    sim_info['plotting_this_iteration'] = (savefreq_fig!=None and i%savefreq_fig == 0)
    sim_info['data_dump_this_iteration'] = (savefreq_dd!=None and (i%savefreq_dd == 0 or i==int(T/dt)-1))
    sim_info['get_fluid_velocity_this_iteration'] = False
    sim_info['measure_one_timestep_correlator'] = _config.get('measure_one_timestep_correlator', False)
    return sim_info

@ex.automain
def main(_config, _run):
    ## Load local copies of the parameters needed in main
    run_id = _config.get('run_id', 0)

    ## Setup Folders
    uid = uuid.uuid4()
    data_dir = f'/tmp/SB-{run_id}-{uid}'
    os.makedirs(data_dir)

    ## Initialize particles
    pXs = (np.random.rand(_config['n_part'],2)-.5)*2*_config['L']
    pVs = np.zeros_like(pXs)
    acc = np.zeros(len(pXs))
    ms  = _config['m_init']*np.ones(len(pXs))

    if _config.get( 'use_interpolated_fluid_velocities' , False):
        print('WARNING: Using interpolated fluid velocities can yield disagreements. The interpolation is correct for most points. However, for some the difference can be relatively large.')

    ## Initialize information dict
    sim_info = {'data_dir': data_dir}

    ## Integration loop
    N_steps = int(_config['T']/_config['dt'])
    for i in tqdm(range(N_steps), disable = _config.get('sweep_experiment', False)):
        if _config.get ('sweep_experiment', False) and (i%50)==0:
            print(f"[{datetime.datetime.now()}] Run {_config.get('run_id', 0)}: Doing step {i+1: >6} of {N_steps}")

        sim_info = get_sim_info(sim_info, _config, i)
        activation_fn = activation_fn_dispatcher(_config, sim_info['t'])
        if sim_info.get('measure_one_timestep_correlator', False):
            pXs_old = deepcopy(pXs)
        pXs, pVs, acc, ms, fXs, fVs, M = integrate_one_timestep(pXs = pXs,
                                                             pVs = pVs,
                                                             acc = acc,
                                                             ms  = ms,
                                                             activation_fn = activation_fn,
                                                             sim_info = sim_info,
                                                             _config = _config,
                                                             get_fluid_velocity=sim_info['get_fluid_velocity_this_iteration'],
                                                             use_interpolated_fluid_velocities=_config.get('use_interpolated_fluid_velocities', False))

        do_measurements(ex = ex,
                        _config = _config,
                        _run = _run,
                        sim_info = sim_info,
                        pXs = pXs,
                        pVs = pVs,
                        acc = acc,
                        ms = ms,
                        fXs = fXs,
                        fVs = fVs,
                        plotting_this_iteration = sim_info['plotting_this_iteration'],
                        save_all_data_this_iteration = sim_info['data_dump_this_iteration'])
        if sim_info.get('measure_one_timestep_correlator', False):
            do_one_timestep_correlation_measurement(ex = ex,
                                                    _config = _config,
                                                    _run = _run,
                                                    sim_info = sim_info,
                                                    pXs = pXs,
                                                    pXs_old = pXs_old)

    post_run_hooks(ex, _config, _run, data_dir)


def run_one(sim, do_local=True, do_S3=False, folder_modifier=None):
    from IAMS.runners.SpringBoxRunner import ex, do_local_storage, do_s3_storage
    if do_local:
        do_local_storage(folder_modifier=folder_modifier)
    if do_S3:
        do_s3_storage(folder_modifier=folder_modifier)
    ex.run(config_updates=sim, options={'--force': True})

def run_all_dask_local(sim_list, n_tasks, **kwargs):
    lazy_results = []
    client = Client(threads_per_worker=1, n_workers = n_tasks)
    for sim in sim_list:
        lazy_results.append(dask.delayed(run_one(sim, **kwargs)))
    dask.compute(*lazy_results)

from ..helper import DEFAULT_QUEUE_LOCATION, write_queued_experiments
def run_all_dask_local_from_json(n_tasks, queue_file=DEFAULT_QUEUE_LOCATION, **kwargs):
    from ..helper import get_queued_experiments
    run_all_dask_local(get_queued_experiments(queue_file), n_tasks, **kwargs)

def get_slurm_script(user, time, num_sims, user_email=None):
    if user_email is None:
        user_email = user+"@caltech.edu"
    return f"""#!/bin/bash
#SBATCH --job-name="Springbox {user}"
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

def get_main_script_cluster():
    return """import os
from IAMS.helper import get_ith_simulation
from IAMS.runners.SpringBoxRunner import run_one
slurm_task_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", "0"))
sim = get_ith_simulation(slurm_task_id, "queue.json")
run_one(sim)
"""

def generate_cluster_submission(list_of_sims, username, time):
    uid = str(hex(hash(uuid.uuid4())))[2:]
    uid = f'SB-{uid}'
    slurm_str = get_slurm_script(username, time, len(list_of_sims))
    main_script = get_main_script_cluster()
    os.makedirs(uid)
    write_queued_experiments(list_of_sims, queue_file_location = f'{uid}/queue.json')
    with open(f'{uid}/submit.sh', 'w') as f:
        f.write(slurm_str)
    with open(f'{uid}/main.py', 'w') as f:
        f.write(main_script)
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
