import IAMS.helper as h
import sacred
from pprint import pprint

for i in range(h.get_number_of_queued_experiments('randomized-fraction.json')):
    ex = sacred.Experiment()
    @ex.main
    def _main(_config):
        pprint(_config)

    _main(h.get_ith_simulation(i, queue_file_location='randomized-fraction.json'))
