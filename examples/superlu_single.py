#! /usr/bin/env python3

"""
Example of invocation of this script:
python superlu.py -nodes 1 -cores 32 -ntask 20 -nrun 800 -machine cori

where:
    -nodes is the number of compute nodes
    -cores is the number of cores per node
    -ntask is the number of different matrix sizes that will be tuned
    -nrun is the number of calls per task 
    -machine is the name of the machine
"""
 
################################################################################

import sys
import os
import numpy as np
import argparse
import pickle

import mpi4py
from mpi4py import MPI
from array import array

sys.path.insert(0, os.path.abspath(__file__ + "/../../GPTune/"))

from computer import Computer
from options import Options
from data import Data
from data import Categoricalnorm
from gptune import GPTune

from autotune.problem import *
from autotune.space import *
from autotune.search import *


################################################################################
def objectives(point):                  # should always use this name for user-defined objective function
    
	matrix = point['matrix']
	COLPERM = point['COLPERM']
	LOOKAHEAD = point['LOOKAHEAD']
	nprows = point['nprows']
	nproc = point['nproc']
	NSUP = point['NSUP']
	NREL = point['NREL']
	nthreads   = int(nprocmax / nproc) 
	npcols     = int(nproc / nprows)
	params = [matrix, 'COLPERM', COLPERM, 'LOOKAHEAD', LOOKAHEAD, 'nthreads', nthreads, 'nprows', nprows, 'npcols', npcols, 'NSUP', NSUP, 'NREL', NREL]
	RUNDIR = os.path.abspath(__file__ + "/../superlu_dist/build/EXAMPLE")
	INPUTDIR = os.path.abspath(__file__ + "/../superlu_dist/EXAMPLE/")
	TUNER_NAME = os.environ['TUNER_NAME']
	nproc     = int(nprows * npcols)

	""" pass some parameters through environment variables """	
	info = MPI.Info.Create()
	envstr= 'OMP_NUM_THREADS=%d\n' %(nthreads)   
	envstr+= 'NREL=%d\n' %(NREL)   
	envstr+= 'NSUP=%d\n' %(NSUP)   
	info.Set('env',envstr)

	""" use MPI spawn to call the executable, and pass the other parameters and inputs through command line """
	print('exec', "%s/pddrive_spawn"%(RUNDIR), 'args', ['-c', '%s'%(npcols), '-r', '%s'%(nprows), '-l', '%s'%(LOOKAHEAD), '-p', '%s'%(COLPERM), '%s/%s'%(INPUTDIR,matrix)], 'nproc', nproc, 'env', 'OMP_NUM_THREADS=%d' %(nthreads), 'NSUP=%d' %(NSUP), 'NREL=%d' %(NREL)  )
	comm = MPI.COMM_SELF.Spawn("%s/pddrive_spawn"%(RUNDIR), args=['-c', '%s'%(npcols), '-r', '%s'%(nprows), '-l', '%s'%(LOOKAHEAD), '-p', '%s'%(COLPERM), '%s/%s'%(INPUTDIR,matrix)], maxprocs=nproc,info=info)

	""" gather the return value using the inter-communicator, also refer to the INPUTDIR/pddrive_spawn.c to see how the return value are communicated """																	
	tmpdata = array('f', [0,0])
	comm.Reduce(sendbuf=None, recvbuf=[tmpdata,MPI.FLOAT],op=MPI.MAX,root=mpi4py.MPI.ROOT) 
	comm.Disconnect()	

	if(target=='time'):	
		retval = tmpdata[0]
		print(params, ' superlu time: ', retval)

	if(target=='memory'):	
		retval = tmpdata[1]
		print(params, ' superlu memory: ', retval)

	return retval 
	
	
def main():

	global ROOTDIR
	global nodes
	global cores
	global target
	global nprocmax
	global nprocmin

	# Parse command line arguments

	parser = argparse.ArgumentParser()

	# Problem related arguments
	# parser.add_argument('-mmax', type=int, default=-1, help='Number of rows')
	# parser.add_argument('-nmax', type=int, default=-1, help='Number of columns')
	# Machine related arguments
	parser.add_argument('-nodes', type=int, default=1, help='Number of machine nodes')
	parser.add_argument('-cores', type=int, default=1, help='Number of cores per machine node')
	parser.add_argument('-machine', type=str, help='Name of the computer (not hostname)')
	# Algorithm related arguments
	parser.add_argument('-optimization', type=str, help='Optimization algorithm (opentuner, spearmint, mogpo)')
	parser.add_argument('-ntask', type=int, default=-1, help='Number of tasks')
	parser.add_argument('-nruns', type=int, help='Number of runs per task')
	parser.add_argument('-truns', type=int, help='Time of runs')
	# Experiment related arguments
	parser.add_argument('-jobid', type=int, default=-1, help='ID of the batch job') #0 means interactive execution (not batch)

	args   = parser.parse_args()

	# Extract arguments

	# mmax = args.mmax
	# nmax = args.nmax
	ntask = args.ntask
	nodes = args.nodes
	cores = args.cores
	machine = args.machine
	optimization = args.optimization
	nruns = args.nruns
	truns = args.truns
	# JOBID = args.jobid


	os.environ['MACHINE_NAME']=machine
	os.environ['TUNER_NAME']='GPTune'
	TUNER_NAME = os.environ['TUNER_NAME']


	nprocmax = nodes*cores-1
	nprocmin = nodes
	# matrices = ["big.rua", "g4.rua", "g20.rua"]
	matrices = ["Si2.rb", "SiH4.rb", "SiNa.rb", "Na5.rb", "benzene.rb", "Si10H16.rb", "Si5H12.rb", "SiO.rb", "Ga3As3H12.rb","H2O.rb"]
	# matrices = ["Si2.rb", "SiH4.rb", "SiNa.rb", "Na5.rb", "benzene.rb", "Si10H16.rb", "Si5H12.rb", "SiO.rb", "Ga3As3H12.rb", "GaAsH6.rb", "H2O.rb"]

	# Task parameters
	matrix    = Categoricalnorm (matrices, transform="onehot", name="matrix")

	# Input parameters
	COLPERM   = Categoricalnorm (['2', '4'], transform="onehot", name="COLPERM")
	LOOKAHEAD = Integer     (5, 20, transform="normalize", name="LOOKAHEAD")
	nprows    = Integer     (1, nprocmax, transform="normalize", name="nprows")
	nproc     = Integer     (nprocmin, nprocmax, transform="normalize", name="nproc")
	NSUP      = Integer     (30, 300, transform="normalize", name="NSUP")
	NREL      = Integer     (10, 40, transform="normalize", name="NREL")	
	result   = Real        (float("-Inf") , float("Inf"), transform="normalize", name="r")
	IS = Space([matrix])
	PS = Space([COLPERM, LOOKAHEAD, nproc, nprows, NSUP, NREL])
	OS = Space([result])
	cst1 = "NSUP >= NREL"
	cst2 = "nproc >= nprows" # intrinsically implies "p <= nproc"
	constraints = {"cst1" : cst1, "cst2" : cst2}
	models = {}

	""" Print all input and parameter samples """	
	print(IS, PS, OS, constraints, models)



	# target='memory'
	target='time'


	problem = TuningProblem(IS, PS, OS, objectives, constraints, None)
	computer = Computer(nodes = nodes, cores = cores, hosts = None)  

	""" Set and validate options """	
	options = Options()
	options['model_processes'] = 1
	# options['model_threads'] = 1
	options['model_restarts'] = 1
	# options['search_multitask_processes'] = 1
	# options['model_restart_processes'] = 1
	options['distributed_memory_parallelism'] = False
	options['shared_memory_parallelism'] = False
	options['model_class '] = 'Model_LCM'
	options['verbose'] = False

	options.validate(computer = computer)


	""" Intialize the tuner with existing data"""		
	data = Data(problem)
	gt = GPTune(problem, computer = computer, data = data, options = options)



	# """ Building MLA with NI random tasks """
	# NI = ntask
	# NS = nruns
	# (data, model,stats) = gt.MLA(NS=NS, NI=NI, NS1 = max(NS//2,1))
	# print("stats: ",stats)

	""" Building MLA with the given list of tasks """	
	giventask = [["Si2.rb"]]	
	NI = len(giventask)
	NS = nruns
	(data, model,stats) = gt.MLA(NS=NS, NI=NI, Igiven =giventask, NS1 = max(NS//2,1))
	print("stats: ",stats)


	""" Print all input and parameter samples """	
	for tid in range(NI):
		print("tid: %d"%(tid))
		print("    matrix:%s"%(data.I[tid][0]))
		print("    Ps ", data.P[tid])
		print("    Os ", data.O[tid])
		print('    Popt ', data.P[tid][np.argmin(data.O[tid])], 'Yopt ', min(data.O[tid])[0])



def parse_args():

	parser = argparse.ArgumentParser()

	# Problem related arguments
	parser.add_argument('-mmax', type=int, default=-1, help='Number of rows')
	parser.add_argument('-nmax', type=int, default=-1, help='Number of columns')
	# Machine related arguments
	parser.add_argument('-nodes', type=int, default=1, help='Number of machine nodes')
	parser.add_argument('-cores', type=int, default=1, help='Number of cores per machine node')
	parser.add_argument('-machine', type=str, help='Name of the computer (not hostname)')
	# Algorithm related arguments
	parser.add_argument('-optimization', type=str, help='Optimization algorithm (opentuner, spearmint, mogpo)')
	parser.add_argument('-ntask', type=int, default=-1, help='Number of tasks')
	parser.add_argument('-nruns', type=int, help='Number of runs per task')
	parser.add_argument('-truns', type=int, help='Time of runs')
	# Experiment related arguments
	parser.add_argument('-jobid', type=int, default=-1, help='ID of the batch job') #0 means interactive execution (not batch)
	parser.add_argument('-stepid', type=int, default=-1, help='step ID')
	parser.add_argument('-phase', type=int, default=0, help='phase')

	args   = parser.parse_args()
	return args


if __name__ == "__main__":
 
	main()
