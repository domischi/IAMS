from IAMS import helper as h
import numpy as np
from pprint import pprint

## Define a parameter set
sim_parameters = [{ 
        'SIMULATION_TYPE' : {'value': 'ANFDM'},

        # Geometry parameters
        'UnitCell_Geo'        : {'value': 'Square'}, #{'Square''Hexagon''Triangular''Random'}
        'lattice_shape'       : {'value': [50,50]},
        'Global_Geometry'     : {'value': ['Hexagon', 'Rectangle', 'Triangle'], 'iterate_over': True},
        'lattice_dsrdr'       : {'value': 0},
        'rounded'             : {'value': False},
        'round_coeff'         : {'value': 2},
        'AR_xy'               : {'value': [1, 0.5]},
        'AR_fr'               : {'value': 1.},
        'illum_ratio'         : {'value': 1},
        'rhoPower'            : {'value': 1},
        'plot_full_positions' : {'value': True},
        'plot_velocity_plot'  : {'value': False},
        'plot_velocity_map'   : {'value': True},
        'plot_density_map'    : {'value': True},
        'show_plots'          : {'value': False},

        # Integration parameters
        'rhof'      : {'value' : 1},
        'rhoi'      : {'value' : 0.5},
        's0'        : {'value' : 0.2},
        'gamma'     : {'value' : 0.0},
        'T_tot'     : {'value' : 1000},
        'dt'        : {'value' : 0.1},
        'N_frame'   : {'value' : 25},
        'tau_s'     : {'value' : 1},
        'mass'      : {'value' : 10},
        'dump_type' : {'value' : 'json' } ,
        }]

## Write simple queue file
h.write_queued_experiments(sim_parameters, queue_file_location='queue-orig.json')
## Convert into standard format & Save it in the simulation packaged way
sim_parameters = h.extended_sim_dicts_to_simplified(sim_parameters)
h.write_queued_experiments(sim_parameters)
