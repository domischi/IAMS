import sacred
from pprint import pprint
import json
from copy import deepcopy
import logging
import itertools
import random
import numpy as np

DEFAULT_QUEUE_LOCATION = 'queue.json'

def extended_sim_dicts_to_simplified(in_sims, PRESERVE_ORIGINAL=True):
    sims=explode_to_individual_sims(in_sims, PRESERVE_ORIGINAL=PRESERVE_ORIGINAL)
    for sim in sims:
        for k in sim:
            sim[k]=sim[k]['value']
    return sims

def explode_to_individual_sims(global_sim_parameters, PRESERVE_ORIGINAL=True):
    if PRESERVE_ORIGINAL:
        sim_file=deepcopy(global_sim_parameters)
    else:
        sim_file=global_sim_parameters
    for i, sim in enumerate(sim_file):
        for parameter_name, parameter_dict in sim.items():
            if parameter_dict.get('iterate_over', False):
                for val in parameter_dict['value']:
                    new_parameter_dict = {'value': val}
                    new_sim = deepcopy(sim)
                    new_sim[parameter_name]=new_parameter_dict
                    sim_file.append(new_sim)
                del sim_file[i]
                return explode_to_individual_sims(sim_file, PRESERVE_ORIGINAL=False)
    return sim_file

def repeated_simulations(sims, n):
    return [item for sublist in itertools.repeat(sims,n) for item in sublist]

def replace_ndarray_w_list(l_of_experiments):
    for sim in l_of_experiments:
        for q in sim:
            if type(sim[q])==np.ndarray:
                sim[q] = sim[q].tolist()

def write_queued_experiments(l_of_experiments, queue_file_location = DEFAULT_QUEUE_LOCATION):
    replace_ndarray_w_list(l_of_experiments)
    with open(queue_file_location, 'w') as f:
        json.dump(l_of_experiments, f, indent=4, sort_keys=True)

def get_queued_experiments(queue_file_location = DEFAULT_QUEUE_LOCATION):
    with open(queue_file_location, 'r') as f:
        l = json.load(f)
    return l

def get_number_of_queued_experiments(queue_file_location=DEFAULT_QUEUE_LOCATION):
    return len(get_queued_experiments(queue_file_location))

def get_ith_simulation(i, queue_file_location = DEFAULT_QUEUE_LOCATION):
    sims = get_queued_experiments(queue_file_location)
    return sims[i]

def random_selection_of_experiments(sims, max_number=None, fraction=None):
    if max_number is None and fraction is None:
        return sims
    if not fraction is None:
        mn = min([int(len(sims)*fraction), len(sims)])
        if max_number is None:
            max_number = mn
        else:
            logging.warning('Specified both a max_number of simulations as well as a fraction, taking the higher of the two values!')
            max_number = max([max_number, mn])
    max_number = min([max_number, len(sims)]) ## Can't do more than len of simulations
    return random.sample(sims, max_number)

def download_generic_from_s3(bucket, folder, file_name, file_name_local = None):
    if file_name_local is None:
        file_name_local = file_name
    s3 = boto3.client('s3')
    s3.download_file(bucket, f'{folder}/{file_name}', file_name_local)

def download_queue_from_s3(fname, bucket='active-matter-simulations', folder = 'queue-files'):
    download_generic_from_s3(bucket, folder, fname, 'queue.json')
