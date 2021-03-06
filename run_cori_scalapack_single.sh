#!/bin/bash -l
#SBATCH -q premium
#SBATCH -N 32
#SBATCH -t 10:00:00
#SBATCH -J GPTune_scalapack_single
#SBATCH --mail-user=liuyangzhuan@lbl.gov
#SBATCH -C haswell


module load python/3.7-anaconda-2019.07
module unload cray-mpich/7.7.6

module swap PrgEnv-intel PrgEnv-gnu
export MKLROOT=/opt/intel/compilers_and_libraries_2018.1.163/linux/mkl
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/intel/compilers_and_libraries_2018.1.163/linux/mkl/lib/intel64

module load openmpi/4.0.1

export PYTHONPATH=$PYTHONPATH:$PWD/autotune/
export PYTHONPATH=$PYTHONPATH:$PWD/scikit-optimize/
export PYTHONPATH=$PYTHONPATH:$PWD/mpi4py/
export PYTHONPATH=$PYTHONPATH:$PWD/GPTune/
export PYTHONPATH=$PYTHONPATH:$PWD/examples/scalapack-driver/spt/
export PYTHONWARNINGS=ignore

CCC=mpicc
CCCPP=mpicxx
FTN=mpif90

cd examples

rm -rf *.pkl
mpirun --mca pmix_server_max_wait 3600 --mca pmix_base_exchange_timeout 3600 --mca orte_abort_timeout 3600 --mca plm_rsh_no_tree_spawn true -n 1  python ./scalapack_single_loaddata.py -mmax 5000 -nmax 5000 -nodes 128 -cores 4 -ntask 1 -nrun 400 -machine cori -jobid 1 | tee a.out_scalapck_ML_m5000_n5000_nodes128_core4_ntask1_nrun400
