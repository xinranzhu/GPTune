#!/bin/bash
#SBATCH -C haswell
#SBATCH -J test_driver
#SBATCH --qos=regular
#SBATCH -t 02:00:00
#SBATCH --nodes=2
#SBATCH --mail-user=xz584@cornell.edu
#SBATCH --mail-type=ALL
##SBATCH --ntasks=8
##SBATCH --tasks-per-node=8
#SBATCH --cpus-per-task=8
##SBATCH --constraint=haswell

#OpenMP settings:
# export OMP_NUM_THREADS=4
# export OMP_PLACES=threads
# export OMP_PROC_BIND=spread

# comment 
# 8 MPI processes with 4 OpenMP threads per process, each OpenMP thread has 1 physical core

module load python/3.7-anaconda-2019.10
module unload cray-mpich

module swap PrgEnv-intel PrgEnv-gnu
export MKLROOT=/opt/intel/compilers_and_libraries_2019.3.199/linux/mkl
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/intel/compilers_and_libraries_2019.3.199/linux/mkl/lib/intel64:/opt/intel/compilers_and_libraries_2019.3.199/linux/compiler/lib/intel64

# module use /global/common/software/m3169/cori/modulefiles
# module unload openmpi
module load openmpi/4.0.1

export PYTHONPATH=$PYTHONPATH:$PWD/autotune/
export PYTHONPATH=$PYTHONPATH:$PWD/scikit-optimize/
export PYTHONPATH=$PYTHONPATH:$PWD/mpi4py/
export PYTHONPATH=$PYTHONPATH:$PWD/GPTune/
export PYTHONPATH=$PYTHONPATH:$PWD/examples/scalapack-driver/spt/
export PYTHONPATH=$PYTHONPATH:$PWD/hypre_example/hypre_driver/
export PYTHONWARNINGS=ignore

CCC=mpicc
CCCPP=mpicxx
FTN=mpif90

# test hypredriver
cd hypre_example/hypre_driver
# srun -n 16 -c 8 --cpu_bind=cores mpirun --mca pmix_server_max_wait 3600 --mca pmix_base_exchange_timeout 3600 --mca orte_abort_timeout 3600 --mca plm_rsh_no_tree_spawn true -n 1 --N 8 python ./hypredriver.py > log_test2.txt
mpirun --mca pmix_server_max_wait 3600 --mca pmix_base_exchange_timeout 3600 --mca orte_abort_timeout 3600 --mca plm_rsh_no_tree_spawn true -n 1 --N 8 python ./hypredriver.py 2>&1 | tee log_test2.txt
