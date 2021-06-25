import boto3
import uuid
import sacred
from pprint import pprint
import json
from copy import deepcopy
import logging
import itertools
import random
import numpy as np

DEFAULT_QUEUE_LOCATION = 'queue.json'

def convert_iterate_over_to_nested_lists(l_in, PRESERVE_ORIGINAL=True):
    if PRESERVE_ORIGINAL:
        l_out=deepcopy(l_in)
    else:
        l_out=l_in
    if type(l_out)==list:
        return [convert_iterate_over_to_nested_lists(l) for l in l_out]
    if type(l_out)==dict :
        if all([type(v) == dict for v in l_out.values()]):
            for k in l_out:
                if not 'iterate_over' in l_out[k]:
                    l_out[k] = l_out[k]['value']
        for k in l_out:
            if type(l_out[k]) == dict and 'iterate_over' in l_out[k]:
                l = []
                for v in l_out[k]['value']:
                    sim = deepcopy(l_out)
                    sim[k]=v
                    l.append(sim)
                return convert_iterate_over_to_nested_lists(l) ## possibly have to still expand underlying lists
        ## No more to expand, can return the original list
        return l_out
    else:
        return l_out

def flatten_nested_list(x):
    result = []
    for el in x:
        if type(el) == list:
            result.extend(flatten_nested_list(el))
        else:
            result.append(el)
    return result

def extended_sim_dicts_to_simplified(global_sim_parameters, PRESERVE_ORIGINAL=True):
    nested_list = convert_iterate_over_to_nested_lists(global_sim_parameters, PRESERVE_ORIGINAL=PRESERVE_ORIGINAL)
    return flatten_nested_list(nested_list)


def repeated_simulations(sims, n):
    return [item for sublist in itertools.repeat(sims,n) for item in sublist]

def replace_ndarray_w_list(sims):
    if type(sims)==list:
        return [replace_ndarray_w_list(l) for l in sims]
    if type(sims)==dict:
        return {replace_ndarray_w_list(k):replace_ndarray_w_list(v) for k,v in sims.items()}
    if type(sims)==np.ndarray:
        return [replace_ndarray_w_list(r) for r in sims]
    if type(sims)==np.int64:
        return int(sims)
    else:
        return sims

def write_queued_experiments(l_of_experiments, queue_file_location = DEFAULT_QUEUE_LOCATION):
    l = replace_ndarray_w_list(l_of_experiments)
    with open(queue_file_location, 'w') as f:
        json.dump(l, f, indent=4, sort_keys=True)

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
    download_generic_from_s3(bucket, folder, fname)

def upload_generic_to_s3(bucket, folder, file_name, file_name_local = None):
    if file_name_local is None:
        file_name_local = file_name
    s3 = boto3.client('s3')
    s3.upload_file(file_name_local, bucket, f'{folder}/{file_name}')

def upload_queue_to_s3(fname, bucket='active-matter-simulations', folder = 'queue-files'):
    uid = str(uuid.uuid4())
    upload_generic_to_s3(bucket, folder, uid+'.json', file_name_local=fname)
    return uid
