# Integrated Active Matter Simulations (IAMS)

## Goal:

Coordinate all numerical experiments of the Thomson Lab into one framework. In particular, we want to 
    (1) Store all experiments to a common database, which we can easily query. 
    (2) Have a simple framework setup which allows rapidly generating the required files with run instructions.
    (3) Have our codes containerized, for simple embarassingly parallel setup.

## Installation

In order to install the project:
- Clone the repo recursively:
    - `mkdir -p ~/src`
    - `cd ~/src`
    - `git clone --recurse-submodules https://github.com/domischi/IAMS.git`
- Add the path to the PYTHONPATH
    `echo 'export PYTHONPATH=$PYTHONPATH:$HOME/src/IAMS' >> ~/.bashrc `
- Then reload your bash environment to reflect the changes
    `source ~/.bashrc`

## Getting Started

A great place to start if you know some python is to navigate into the example folders and checking out examples 3-5 that involve Springbox and ANFDM. If you prefer a more visual approach, start off with navigating to the gui folder and start your journey with `python main.py`.
