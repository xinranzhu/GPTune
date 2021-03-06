#! /usr/bin/env python3

"""
Example of invocation of this script:

python scalapack.py -mmax 5000 -nmax 5000 -nodes 1 -cores 32 -ntask 20 -nrun 800 -machine cori -jobid 0

where:
    -mmax (nmax) is the maximum number of rows (columns) in a matrix
    -nodes is the number of compute nodes
    -cores is the number of cores per node
    -ntask is the number of different matrix sizes that will be tuned
    -nrun is the number of calls per task 
    -machine is the name of the machine
    -jobid is optional. You can always set it to 0.
"""

################################################################################

from pdqrdriver import pdqrdriver
from autotune.search import *
from autotune.space import *
from autotune.problem import *
from gptune import GPTune
from data import Data
from options import Options
from computer import Computer
import sys
import os
import numpy as np
import argparse
import pickle
from random import *
from callopentuner import OpenTuner

sys.path.insert(0, os.path.abspath(__file__ + "/../../GPTune/"))


sys.path.insert(0, os.path.abspath(__file__ + "/../scalapack-driver/spt/"))


################################################################################
''' The objective function required by GPTune. '''


# should always use this name for user-defined objective function
def objectives(point):
    m = point['m']
    n = point['n']
    mb = point['mb']
    nb = point['nb']
    nproc = point['nproc']
    p = point['p']

    # this become useful when the parameters returned by TLA1 do not respect the constraints
    if(nproc == 0 or p == 0 or nproc < p):
        print('Warning: wrong parameters for objective function!!!', nproc,p)
        return 1e12

    nthreads = int(nprocmax / nproc)
    q = int(nproc / p)

    params = [('QR', m, n, nodes, cores, mb, nb, nthreads, nproc, p, q, 1.)]
    elapsedtime = pdqrdriver(params, niter=3, JOBID=JOBID)
    print(params, ' scalapack time: ', elapsedtime)

    return elapsedtime




# should always use this name for user-defined model function
def models(point):
    m = point['m']
    n = point['n']
    nproc = point['nproc']
    p = point['p']
    mb = point['mb']
    nb = point['nb']

    # this become useful when the parameters returned by TLA1 do not respect the constraints
    if(nproc == 0 or p == 0 or nproc < p):
        print('Warning: wrong parameters for models function!!!', nproc,p)
        return 1e12

    # nthreads = int(nprocmax / nproc)
    q = int(nproc / p)

    b = max(mb,nb)
    # elapsedtime = (2*n**2*(3*m-n)/3/nproc + b*n**2/2/q + 3*b*n*(2*m-n)/2/p + b**2*n/3/p)/(max(m,n)*min(m,n)**2)
    elapsedtime = max(m,n)*min(m,n)**2/nproc/(max(m,n)*min(m,n)**2)

    return [elapsedtime]


def main():

    global ROOTDIR
    global nodes
    global cores
    global JOBID
    global nprocmax
    global nprocmin

    # Parse command line arguments
    args = parse_args()

    mmax = args.mmax
    nmax = args.nmax
    ntask = args.ntask
    nodes = args.nodes
    cores = args.cores
    machine = args.machine
    nruns = args.nruns
    truns = args.truns
    JOBID = args.jobid

    os.environ['MACHINE_NAME'] = machine
    os.environ['TUNER_NAME'] = 'GPTune'
    os.system("mkdir -p scalapack-driver/bin/%s; cp ../build/pdqrdriver scalapack-driver/bin/%s/.;" %(machine, machine))

    nprocmax = nodes*cores-1  # YL: there is one proc doing spawning
    nprocmin = nodes

    mmin=128
    nmin=128
    m = Integer(mmin, mmax, transform="normalize", name="m")
    n = Integer(nmin, nmax, transform="normalize", name="n")
    mb = Integer(1, 128, transform="normalize", name="mb")
    nb = Integer(1, 128, transform="normalize", name="nb")
    nproc = Integer(nprocmin, nprocmax, transform="normalize", name="nproc")
    p = Integer(1, nprocmax, transform="normalize", name="p")
    r = Real(float("-Inf"), float("Inf"), name="r")

    IS = Space([m, n])
    PS = Space([mb, nb, nproc, p])
    OS = Space([r])
    cst1 = "mb * p <= m"
    cst2 = "nb * nproc <= n * p"
    cst3 = "nproc >= p"
    constraints = {"cst1": cst1, "cst2": cst2, "cst3": cst3}
    print(IS, PS, OS, constraints)

    # problem = TuningProblem(IS, PS, OS, objectives, constraints, models) # use performance models
    problem = TuningProblem(IS, PS, OS, objectives, constraints, None) # no performance model

    computer = Computer(nodes=nodes, cores=cores, hosts=None)
    """ Set and validate options """
    options = Options()
    options['model_processes'] = 1
    # options['model_threads'] = 1
    options['model_restarts'] = 1
    # options['search_multitask_processes'] = 1
    # options['model_restart_processes'] = 1
    # options['model_restart_threads'] = 1

    # options['objective_evaluation_parallelism'] = True

    options['distributed_memory_parallelism'] = False
    options['shared_memory_parallelism'] = False
    # options['mpi_comm'] = None
    options['model_class '] = 'Model_LCM'
    options['verbose'] = False

    options.validate(computer=computer)
    # giventask = [[2000, 2000]]
    # giventask = [[randint(mmin,mmax),randint(nmin,nmax)] for i in range(ntask)]
    giventask = [[460, 500], [800, 690]]


    data = Data(problem)
    gt = GPTune(problem, computer=computer, data=data, options=options,driverabspath=os.path.abspath(__file__))

    TUNER_NAME = os.environ['TUNER_NAME']

    if(TUNER_NAME=='GPTune'):
        """ Building MLA with the given list of tasks """
        NI = len(giventask)
        NS = nruns
        (data, model, stats) = gt.MLA(NS=NS, NI=NI, Igiven=giventask, NS1=max(NS//2, 1))
        print("stats: ", stats)
        pickle.dump(gt, open('MLA_nodes_%d_cores_%d_mmax_%d_nmax_%d_machine_%s_jobid_%d.pkl' % (
            nodes, cores, mmax, nmax, machine, JOBID), 'wb'))

        """ Print all input and parameter samples """
        for tid in range(NI):
            print("tid: %d" % (tid))
            print("    m:%d n:%d" % (data.I[tid][0], data.I[tid][1]))
            print("    Ps ", data.P[tid])
            print("    Os ", data.O[tid])
            print('    Popt ', data.P[tid][np.argmin(data.O[tid])], 'Yopt ', min(data.O[tid])[0], 'nth ', np.argmin(data.O[tid]))

        """ Call TLA for 2 new tasks using the constructed LCM model"""
        newtask = [[400, 500], [800, 600]]
        (aprxopts, objval, stats) = gt.TLA1(newtask, NS=None)
        print("stats: ", stats)

        """ Print the optimal parameters and function evaluations"""
        for tid in range(len(newtask)):
            print("new task: %s" % (newtask[tid]))
            print('    predicted Popt: ', aprxopts[tid], ' objval: ', objval[tid])


    if(TUNER_NAME=='opentuner'):
        NI = ntask
        NS = nruns
        (data,stats)=OpenTuner(T=giventask, NS=NS, tp=problem, computer=computer, run_id="OpenTuner", niter=1, technique=None)
        print("stats: ", stats)

        """ Print all input and parameter samples """
        for tid in range(NI):
            print("tid: %d" % (tid))
            print("    t:%d " % (data.I[tid][0]))
            print("    Ps ", data.P[tid])
            print("    Os ", data.O[tid])
            print('    Popt ', data.P[tid][np.argmin(data.O[tid])], 'Oopt ', min(data.O[tid])[0], 'nth ', np.argmin(data.O[tid]))


def parse_args():

    parser = argparse.ArgumentParser()

    # Problem related arguments
    parser.add_argument('-mmax', type=int, default=-1, help='Number of rows')
    parser.add_argument('-nmax', type=int, default=-
                        1, help='Number of columns')
    # Machine related arguments
    parser.add_argument('-nodes', type=int, default=1,
                        help='Number of machine nodes')
    parser.add_argument('-cores', type=int, default=1,
                        help='Number of cores per machine node')
    parser.add_argument('-machine', type=str,
                        help='Name of the computer (not hostname)')
    # Algorithm related arguments
    parser.add_argument('-optimization', type=str,
                        help='Optimization algorithm (opentuner, spearmint, mogpo)')
    parser.add_argument('-ntask', type=int, default=-1, help='Number of tasks')
    parser.add_argument('-nruns', type=int, help='Number of runs per task')
    parser.add_argument('-truns', type=int, help='Time of runs')
    # Experiment related arguments
    # 0 means interactive execution (not batch)
    parser.add_argument('-jobid', type=int, default=-
                        1, help='ID of the batch job')
    parser.add_argument('-stepid', type=int, default=-1, help='step ID')
    parser.add_argument('-phase', type=int, default=0, help='phase')

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    main()
