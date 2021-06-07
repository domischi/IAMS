from IAMS import helper as h
import numpy as np
import sacred
from pprint import pprint

## Define a parameter set
sim_parameters = [
        {
            'val1': {'value': 0.},
            'val2': {'value': 4}, ## A value not to expand (default)
            'val3': {'value': np.linspace(0,1,101), 'iterate_over': True},
            'val4': {'value':np.linspace(0,1,101), 'iterate_over': True},
            }
    ]
sim_parameters = h.extended_sim_dicts_to_simplified(sim_parameters)

# Queue a grid search
h.write_queued_experiments(sim_parameters, queue_file_location='grid-search.json')
print(h.get_number_of_queued_experiments('grid-search.json'))

# Queue a grid search with repeated simulations for statistics
h.write_queued_experiments(h.repeated_simulations(sim_parameters, n=3), queue_file_location='grid-search-repeated.json')
print(h.get_number_of_queued_experiments('grid-search-repeated.json'))

# Queue a randomized search based on the number of simulations
h.write_queued_experiments(h.random_selection_of_experiments(sim_parameters, max_number=25), queue_file_location='randomized-number.json')
print(h.get_number_of_queued_experiments('randomized-number.json'))

# Queue a randomized search based on a fraction of phase space
h.write_queued_experiments(h.random_selection_of_experiments(sim_parameters, fraction=.01), queue_file_location='randomized-fraction.json')
print(h.get_number_of_queued_experiments('randomized-fraction.json'))
