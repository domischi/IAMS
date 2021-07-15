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
import IAMS.simulators.SpringBox.SpringBox as SB
from IAMS.simulators.SpringBox.SpringBox.integrator import integrate_one_timestep
from IAMS.simulators.SpringBox.SpringBox.activation import activation_fn_dispatcher
from IAMS.simulators.SpringBox.SpringBox.post_run_hooks import post_run_hooks
from IAMS.simulators.SpringBox.SpringBox.measurements import do_measurements, do_one_timestep_correlation_measurement
import uuid
import boto3
from ..helper import DEFAULT_QUEUE_LOCATION
from .runner_helper import *

ex = sacred.Experiment()
ex.dependencies.add(sacred.dependencies.PackageDependency("SpringBox",SB.__version__))

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
        activation_fn = activation_fn_dispatcher(_config, sim_info['t'], experiment = ex)
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
    from IAMS.runners.SpringBoxRunner import ex
    from IAMS.runners.runner_helper import do_local_storage, do_s3_storage
    if do_local:
        do_local_storage(ex, folder_modifier=folder_modifier)
    if do_S3:
        do_s3_storage(ex, 'SpringBox', folder_modifier=folder_modifier)
    ex.run(config_updates=sim, options={'--force': True})

def run_all_dask_local(sim_list, n_tasks, **kwargs):
    run_all_dask_local_from_run_one(run_one, sim_list, n_tasks, **kwargs)

def run_all_dask_local_from_json(n_tasks, queue_file=DEFAULT_QUEUE_LOCATION, **kwargs):
    from ..helper import get_queued_experiments
    run_all_dask_local(get_queued_experiments(queue_file), n_tasks, **kwargs)
