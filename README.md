# Structured Compression and Sharing of Representational Space for Continual Learning

This repository contains code to accompany arXiv submission on Structured Compression and Sharing of Representational Space for Continual Learning. https://arxiv.org/pdf/2001.08650.pdf

The experiments with CIFAR-10 dataset in the paper can be reproduced by going to PCA_CL_github directory. The setup outputs the data for our method as shown in Figure 5b and 7a of the paper. The run_cfiar10.sh file contains the run parameters and finalized hyperparameters. They can be changed by editing the file and source the file to run the experiment using the following command : 

$source run_cifar10.sh 

Trained models can be found at PCA_CL_github/PARAM/CIFAR10_task direactory. To run the trained model, comment out the training command and uncomment the test command in run_cifar10.sh file and then source it. 
