import os
import shutil
import datetime
import uuid
from copy import deepcopy
import numpy as np
from tqdm import tqdm
import sacred
import numba
import warnings
warnings.simplefilter('ignore', category=numba.NumbaWarning)
from IAMS.simulators.ANFDM.ANFDM import __version__ as anfdm_version 
import IAMS.simulators.ANFDM.ANFDM.active_net_dynamics as ANFDM
import uuid
import boto3
from ..helper import DEFAULT_QUEUE_LOCATION
from .runner_helper import *

ex = sacred.Experiment()
ex.dependencies.add(sacred.dependencies.PackageDependency("ANFDM",anfdm_version))

@ex.config
def cfg():
    pass

@ex.automain
def main(_config, _run):
    # Initialize network
    net = ANFDM.random_network(_config, experiment = ex)

    # Integrate it up
    integration_method = _config.get('integration_method', 'inertial').lower()
    if integration_method == 'inertial':
        net.Inertial_Dynamics(_config['T_tot'],
                          _config['dt'],
                          _config['mass'],
                          _config['gamma'],
                          _config['rhoi'],
                          _config['s0'],
                          _config['tau_s'],
                          N_frame = _config['N_frame']
                          )
    elif integration_method == 'viscous': 
        net.Viscous_Dynamics(_config['T_tot'],
                          _config['dt'],
                          #_config['mass'],
                          _config['gamma'],
                          _config['rhoi'],
                          _config['s0'],
                          _config['tau_s'],
                          N_frame = _config['N_frame']
                          )
    else:
        raise RuntimeError(f"Don't understand integration type {integration_method}")

def run_one(sim, do_local=True, do_S3=False, folder_modifier=None):
    from IAMS.runners.ANFDMRunner import ex
    from IAMS.runners.runner_helper import do_local_storage, do_s3_storage
    if do_local:
        do_local_storage(ex, folder_modifier=folder_modifier)
    if do_S3:
        do_s3_storage(ex, 'ANFDM', folder_modifier=folder_modifier)
    ex.run(config_updates=sim, options={'--force': True})

def run_all_dask_local(sim_list, n_tasks, **kwargs):
    run_all_dask_local_from_run_one(run_one, sim_list, n_tasks, **kwargs)

def run_all_dask_local_from_json(n_tasks, queue_file=DEFAULT_QUEUE_LOCATION, **kwargs):
    from ..helper import get_queued_experiments
    run_all_dask_local(get_queued_experiments(queue_file), n_tasks, **kwargs)
