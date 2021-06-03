from sacred import Experiment
from sacred.observers import S3Observer

ex = Experiment()
ex.observers.append(S3Observer(bucket='active-matter-simulations',
                               basedir='simple-storage'))

@ex.automain
def run_simulation():
    print('Hello World!')

