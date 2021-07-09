import boto3
import os
import uuid
import sacred
from pprint import pprint
import json
from copy import deepcopy
import logging
import itertools
import random
import numpy as np
import re

DEFAULT_QUEUE_LOCATION = 'queue.json'

def contains_iterate_over(d):
    assert(type(d)==dict)
    for v in d.values():
        if isinstance(v, dict) and v.get('iterate_over', False):
            return True
    return False

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
            if isinstance(l_out[k], dict) and 'iterate_over' in l_out[k]:
                if l_out[k]['iterate_over']:
                    l = []
                    for v in l_out[k]['value']:
                        sim = deepcopy(l_out)
                        sim[k]=v
                        l.append(sim)
                    return convert_iterate_over_to_nested_lists(l) ## possibly have to still expand underlying lists
                else:
                    sim = deepcopy(l_out)
                    sim[k]=l_out[k]['value']
                    return convert_iterate_over_to_nested_lists([sim]) ## possibly have to still expand underlying lists
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

def download_generic_from_s3(bucket, folder, file_name, file_name_local = None, client=None):
    if file_name_local is None:
        file_name_local = file_name
    if client is None:
        client = boto3.client('s3')
    print('\n'*5)
    print(f'{folder}/{file_name}')
    print('\n'*5)
    client.download_file(bucket, f'{folder}/{file_name}', file_name_local)

def download_queue_from_s3(uid, resource_folder_name, bucket='active-matter-simulations', folder = 'queue-files'):
    s3 = boto3.client('s3')
    ## Download queue file
    download_generic_from_s3(bucket, folder, uid+'.json', client=s3)
    ## Download the resources as well
    # Make folder
    os.makedirs(resource_folder_name)
    # List all objects in the corresponding bucket/key
    obj_list = [o['Key'] for o in s3.list_objects(Bucket=bucket, Prefix=f'{folder}/{uid}/')['Contents']]
    # Download each of them
    for o in obj_list:
        fname = o.split('/')[-1]
        download_generic_from_s3(bucket, folder=f'{folder}/{uid}', file_name = fname , file_name_local = f'{resource_folder_name}/{fname}', client=s3)


def upload_generic_to_s3(bucket, folder, file_name, file_name_local = None, client=None):
    if file_name_local is None:
        file_name_local = file_name
    if client is None:
        client = boto3.client('s3')
    client.upload_file(file_name_local, bucket, f'{folder}/{file_name}')

def upload_queue_to_s3(fname, resource_folder, bucket='active-matter-simulations', folder = 'queue-files'):
    uid = str(uuid.uuid4())
    ## Initialize once as we now have to upload a few files
    s3 = boto3.client('s3')

    ## Upload resources to S3
    if os.path.exists(resource_folder):
        for f in os.listdir(resource_folder):
            if os.path.isfile(resource_folder+'/'+f):
                upload_generic_to_s3(bucket, folder+f'/{uid}', f, file_name_local=f'{resource_folder}/{f}', client=s3)
    ## Upload main queue file to S3
    upload_generic_to_s3(bucket, folder, uid+'.json', file_name_local=fname, client=s3)
    return uid

def is_valid_slurm_time(t):
    ## Acceptable time formats include "minutes", "minutes:seconds", "hours:minutes:seconds", "days-hours", "days-hours:minutes" and "days-hours:minutes:seconds"
    ## (https://slurm.schedmd.com/sbatch.html)
    re_list = [
            r"^\d+$"                   , # "minutes"
            r"^\d+:\d{2}$"             , # "minutes:seconds"
            r"^\d+:\d{2}:\d{2}$"       , # "hours:minutes:seconds"
            r"^\d+-\d{2}$"             , # "days-hours"
            r"^\d+-\d{2}:\d{2}$"       , # "days-hours:minutes"
            r"^\d+-\d{2}:\d{2}:\d{2}$" , # "days-hours:minutes:seconds"
            ]
    return any([bool(re.match(r, t)) for r in re_list])
