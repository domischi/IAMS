import IAMS.helper as h
import sacred
from pprint import pprint

ex = sacred.Experiment()
ex.add_config(h.get_ith_simulation(3, queue_file_location='randomized-number.json'))

@ex.automain
def _main(_config):
    pprint(_config)
