from IAMS import helper as h
import numpy as np
from pprint import pprint

## Define a parameter set
vx = 0.5
#particle_density=310
particle_density=100
L=2
sim_parameters = [
        {
    ## Simulation parameters
    'savefreq_fig' :{'value': 1},
    'savefreq_data_dump' :{'value': 1},
    'dt' :{'value': .01},
    'T' :{'value': .1},
    'particle_density' :{'value': particle_density},
    'MAKE_VIDEO' :{'value': True},
    'SAVEFIG'    :{'value': True},
    'const_particle_density' :{'value': False},

    ## Geometry parameters / Activation Fn
    'activation_fn_type' :{'value': 'video'}, # For the possible choices, see the activation.py file
    'activation_image_filepath' :{'value': 'resources/activation-*.png'}, # For the possible choices, see the activation.py file
    'L' :{'value': L},
    'n_part' :{'value': particle_density * ((2*L)**2)},

    ## Interaction parameters
    # Particle properties
    'activation_decay_rate' :{'value': [0, np.inf], 'iterate_over': True}, # Ex. at dt=0.01 this leads to an average deactivation of 10% of the particles
    # Spring properties
    'spring_cutoff' :{'value': L}, # Always have a same average of particles that interact},
    }
    ]

## Write simple queue file
h.write_queued_experiments(sim_parameters, queue_file_location='queue.json')
## Convert into standard format & Save it in the simulation packaged way
sim_parameters = h.extended_sim_dicts_to_simplified(sim_parameters)
h.write_queued_experiments(sim_parameters)
