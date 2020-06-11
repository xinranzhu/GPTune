import numpy as np
import os, sys, re
# import mpi4py
# from mpi4py import MPI

MACHINE_NAME = 'cori'
TUNER_NAME = 'GPTune'

# paths
ROOTDIR = os.path.abspath(os.path.join(os.path.realpath(__file__), os.pardir))
EXPDIR = os.path.abspath(os.path.join(ROOTDIR, "exp", MACHINE_NAME + '/' + TUNER_NAME))
EXCUDIR = os.path.abspath(os.path.join(ROOTDIR, "hypre/src/test/ij "))


solver = 3
max_setup_time = 100.
max_solve_time = 100.
coeffs_c = "-c 1 1 1 " # specify c-coefficients in format "-c 1 1 1 " 
coeffs_a = "-a 0 0 0 " # specify a-coefficients in format "-a 1 1 1 " leave as empty string for laplacian and Poisson problems
problem_name = "-laplacian " # "-difconv " for convection-diffusion problems to include the a coefficients

nx = 60
ny = 50
nz = 80
Px = 2
Py = 2
Pz = 2
strong_threshold = 0.25 # real [0, 1], default = 0.25
trunc_factor = 0. # real, range: [0, 1], default = 0
P_max_elmts = 4 # int, range: 1:12, default = 4
coarsen_type = 10 # int(cat), range: {0, 1, 2, 3, 4, 6, 8, 10}, default = 10
relax_type = 8 # int(cat), range: {-1 (w/o smoother), 0, 6, 8, 16, 18}, default = 8 = L1-Gauss-Seidel smoother
smooth_type = 6 # int(cat), range = {5, 6, 7, 8, 9}, default = 6 = Schwarz
smooth_num_levels = 0 # int, range = 0:5, default = 0
interp_type = 6 # int(cat), range: {0, 3, 4, 5, 6, 8, 12}, default = 6
agg_num_levels = 0 # int, range: 0:5, default = 0

CoarsTypes = {0:"-cljp ", 1:"-ruge ", 2:"-ruge2b ", 3:"-ruge2b ", 4:"-ruge3c ", 6:"-falgout ", 8:"-pmis ", 10:"-hmis "}
CoarsType = CoarsTypes[coarsen_type]

print(EXPDIR)
outputfilename = os.path.abspath(os.path.join(EXPDIR, f"ijoutput_{nx}_{ny}_{nz}_{Px}_{Py}_{Pz}_{strong_threshold}_{trunc_factor}_{P_max_elmts}_{coarsen_type}_{relax_type}_{smooth_type}_{smooth_num_levels}_{interp_type}_{agg_num_levels}"))
print(outputfilename)

NProc = Px * Py * Pz
Procs = "export OMP_PLACES=threads; export OMP_PROC_BIND=spread; export OMP_NUM_THREADS=1; srun -n %d " % NProc
Size = "-n %d %d %d " % (nx, ny, nz)
ProcTopo = "-P %d %d %d " % (Px, Py, Pz)
StrThr = f"-th {strong_threshold} "
TrunFac = f"-tr {trunc_factor} "
PMax = "-Pmx %d " % P_max_elmts
RelType = "-rlx %d " % relax_type
SmooType = "-smtype %d " % smooth_type
SmooLev = "-smlv %d " % smooth_num_levels 
InterType = "-interptype %d " % interp_type 
AggLev = "-agg_nl %d " % agg_num_levels

command = Procs + EXCUDIR + problem_name + Size + coeffs_c + coeffs_a + f" -solver {solver} " + ProcTopo + StrThr + TrunFac + PMax + RelType + SmooType + SmooLev + InterType + AggLev + CoarsType + "2>&1 | tee " + outputfilename
print(command)

os.system(command)

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

