Integrated Active Matter Simulations (IAMS)

Goal:
Coordinate all numerical experiments of the Thomson Lab into one framework. In particular, we want to 
    (1) Store all experiments to a common database, which we can easily query. 
    (2) Have a simple framework setup which allows rapidly generating the required files with run instructions.
    (3) Have our codes containerized, for simple embarassingly parallel setup.


In order to install the project:
- Clone the repo recursively:
    - `mkdir -p ~/src`
    - `cd ~/src`
    - `git clone --recurse-submodules https://github.com/domischi/IAMS.git`
- Add the path to the PYTHONPATH
    `echo 'export PYTHONPATH=$PYTHONPATH:$HOME/src/IAMS' >> ~/.bashrc `
- Then reload your bash environment to reflect the changes
    `source ~/.bashrc`
