#! /usr/bin/env python3

################################################################################

import sys, os, re
sys.path.insert(0, os.path.abspath(__file__ + "/../../"))
from ztune import *

################################################################################

"""
# Description of the parameters of Hypre AMG:
# Task space:
# nx:    problem size in dimension x
# ny:    problem size in dimension y
# nz:    problem size in dimension z
# cx:    diffusion coefficient for d^2/dx^2
# cy:    diffusion coefficient for d^2/dy^2
# cz:    diffusion coefficient for d^2/dz^2
# ax:    convection coefficient for d/dx
# ay:    convection coefficient for d/dy
# az:    convection coefficient for d/dz
# Input space:
# Px:                processor topology, with NProc = Px*Py*Pz
# Py:                processor topology, with NProc = Px*Py*Pz
# Pz:                processor topology, with NProc = Px*Py*Pz
# strong_threshold:  AMG strength threshold
# trunc_factor:      Truncation factor for interpolation
# P_max_elmts:       Max number of elements per row for AMG interpolation
# coarsen_type:      Defines which parallel coarsening algorithm is used
# relax_type:        Defines which smoother to be used
# smooth_type:       Enables the use of more complex smoothers
# smooth_num_levels: Number of levels for more complex smoothers
# interp_type:       Defines which parallel interpolation operator is used  
# agg_num_levels:    Number of levels of aggressive coarsening
"""

solver = 3
max_setup_time = 100.
max_solve_time = 100.
coeffs_c = "" # specify c-coefficients in format "-c 1 1 1 " 
coeffs_a = "" # specify a-coefficients in format "-a 1 1 1 " leave as empty string for laplacian and Poisson problems
problem_name = "-laplacian " # "-difconv " for convection-diffusion problems to include the a coefficients

# Objective function
def HypreAMG (nx, ny, nz, Px, Py, Pz, strong_threshold, trunc_factor, P_max_elmts, coarsen_type, relax_type, smooth_type, smooth_num_levels, interp_type, agg_num_levels):

    NProc = Px*Py*Pz
    Procs = "export OMP_PLACES=threads; export OMP_PROC_BIND=spread; export OMP_NUM_THREADS=1; srun -n %d " % NProc
    FileName = os.path.abspath(__file__ + "/../hypre/src/test/ij ")
    Problem = problem_name
    Size = "-n %d %d %d " % (nx, ny, nz)
    CoeffsC = coeffs_c
    CoeffsA = coeffs_a
    ProcTopo = "-P %d %d %d " % (Px, Py, Pz)
    StrThr = f"-th {strong_threshold} "
    TrunFac = f"-tr {trunc_factor} "
    PMax = "-Pmx %d " % P_max_elmts
    RelType = "-rlx %d " % relax_type
    SmooType = "-smtype %d " % smooth_type
    SmooLev = "-smlv %d " % smooth_num_levels 
    InterType = "-interptype %d " % interp_type 
    AggLev = "-agg_nl %d " % agg_num_levels

    CoarsTypes = {0:"-cljp ", 1:"-ruge ", 2:"-ruge2b ", 3:"-ruge2b ", 4:"-ruge3c ", 6:"-falgout ", 8:"-pmis ", 10:"-hmis "}
    CoarsType = CoarsTypes[coarsen_type]

    outputfilename = os.path.abspath(__file__ + f"/../hypre/exp/{tunername}/ijoutput_{nx}_{ny}_{nz}_{Px}_{Py}_{Pz}_{strong_threshold}_{trunc_factor}_{P_max_elmts}_{coarsen_type}_{relax_type}_{smooth_type}_{smooth_num_levels}_{interp_type}_{agg_num_levels}")

    command = Procs + FileName + Problem + Size + CoeffsC + CoeffsA + f"-solver {solver} " + ProcTopo + StrThr + TrunFac + PMax + RelType + SmooType + SmooLev + InterType + AggLev + CoarsType + "> " + outputfilename

    print(command)

    os.system(command)

    setup_time = max_setup_time
    solve_time = max_solve_time

    with open(outputfilename,'r') as outputfile:
        while True:
            line = outputfile.readline()
            if not line:
                break
            if 'ERROR' in line:
                break
            if 'Setup phase times' in line:
                outputfile.readline()
                outputfile.readline()
                setup_wallclocktime_str = outputfile.readline()
                time_str = re.findall("\d+\.\d+", setup_wallclocktime_str)
                if time_str:
                    setup_time = float(time_str[0])
            if 'Solve phase times' in line:
                outputfile.readline()
                outputfile.readline()
                solve_wallclocktime_str = outputfile.readline()
                time_str = re.findall("\d+\.\d+", solve_wallclocktime_str)
                if time_str:
                   solve_time = float(time_str[0])

    runtime = setup_time + solve_time
    print("[----- runtime = %f -----]\n" % runtime)

    return runtime

def define_problem(nodes, cores, appname, tunername):

    # Task parameters
    nx                = Integer (name = "nx", range = (10,100))
    ny                = Integer (name = "ny", range = (10,100))
    nz                = Integer (name = "nz", range = (10,100))

    # Input parameters
    Px                = Integer     (name = "Px",                range  = (1, int(nodes*cores)))
    Py                = Integer     (name = "Py",                range  = (1, int(nodes*cores)))
    Pz                = Integer     (name = "Pz",                range  = (1, int(nodes*cores)))
    strong_threshold  = Real        (name = "strong_threshold",  range  = (0, 1))
    trunc_factor      = Real        (name = "trunc_factor",      range  = (0, 0.999))
    P_max_elmts       = Integer     (name = "P_max_elmts",       range  = (1, 12))
    relax_type        = Categorical (name = "relax_type",        values = [0, 3, 6, 8, 13, 16, 18])
    smooth_type       = Categorical (name = "smooth_type",       values = [6, 9])
    smooth_num_levels = Integer     (name = "smooth_num_levels", range  = (0, 5))
    interp_type       = Categorical (name = "interp_type",       values = [0, 3, 4, 6, 7, 8, 12, 13, 14]) 
    agg_num_levels    = Integer     (name = "agg_num_levels",    range  = (0, 5))
    coarsen_type      = Categorical (name = "coarsen_type",      values = [0, 1, 2, 3, 4, 6, 8, 10])

    # Output parameter
    runtime           = Real (name="runtime", range=(float("-Inf"), float("Inf")))

    # Spaces
    TS = Space(params=[nx, ny, nz])
    IS = Space(params=[Px, Py, Pz, strong_threshold, trunc_factor, P_max_elmts, relax_type, smooth_type, smooth_num_levels, interp_type, agg_num_levels, coarsen_type])
    OS = Space(params=[runtime])

    cst1 = f"Px*Py*Pz <= {int(nodes*cores)}"

    constraints = {"cst1" : cst1}

    models = None

#    print(TS, IS, OS, constraints, models)

    z = ZTune(TS, IS, OS, objfun = HypreAMG, cstrs = constraints, objmdls = models, name = f"{appname} Tuner")

    return z

if __name__ == "__main__":

    # Parse command line arguments

    (nodes, cores, NT, NS, NS1, Q, gentasks, appname, tunername) = parse_command_line_arguments()

    # Define Tuning Problem

    z = define_problem(nodes, cores, appname, tunername)

    # Tune

    tune(z, nodes, cores, NT, NS, NS1, Q, gentasks, appname, tunername)

