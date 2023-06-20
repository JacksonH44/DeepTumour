#!/bin/bash
#SBATCH --account=def-sushant
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=5000M
#SBATCH --time=0-02:30
#SBATCH --job-name=transfer_learning_regression
#SBATCH --output=../outputs/SLURM_DEFAULT_OUT/transfer_learning_regression-%j.out
#SBATCH --error=../outputs/SLURM_DEFAULT_OUT/transfer_learning_regression-%j.err

module load python
ENVDIR=/tmp/$RANDOM
virtualenv --no-download $ENVDIR

module load cuda/11.7
module load scipy-stack
source $ENVDIR/bin/activate
pip install --no-index tensorflow
pip install --no-index scikit-learn
python ../src/transfer_learning_regression.py ../outputs/HNE_2
deactivate
rm -rf $ENVDIR