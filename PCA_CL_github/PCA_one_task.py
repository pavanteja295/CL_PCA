from __future__ import print_function
import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt 
from collections import OrderedDict
import numpy as np
import os
import os.path
# from logger import Logger
from cifar10_utilities import*
from tensorboardX import SummaryWriter

########-------------------------------------------- Model Class --------------------------------##################
class Net(nn.Module):
    """Small architechture"""
    def __init__(self,num_classes=2):
        super(Net, self).__init__()
        self.act=OrderedDict()
        self.conv1 = nn.Conv2d(3, 32, 3)
        self.conv2 = nn.Conv2d(32, 32, 3)
        self.drop_outA = nn.Dropout(0.15)
        self.conv3 = nn.Conv2d(32, 64, 3)
        self.conv4 = nn.Conv2d(64,64,3)
        self.drop_outB = nn.Dropout(0.15)
        self.conv5 = nn.Conv2d(64,128,2)
        self.last = nn.Linear(128*4, num_classes)

    def forward(self, x):
        x = self.conv1(x)
        self.act['conv1']=x
        x = F.relu(x)
        x = self.conv2(x)
        self.act['conv2']=x
        x = F.relu(x)
        x = F.max_pool2d(x, 2, 2)
        x = self.drop_outA(x)
        
        x = self.conv3(x)
        self.act['conv3']=x
        x = F.relu(x)
        x = self.conv4(x)
        self.act['conv4']=x
        x = F.relu(x)
        x = F.max_pool2d(x, 2, 2)
        x = self.drop_outB(x)
        
        x = self.conv5(x)
        self.act['conv5']=x
        x = F.relu(x)
        x = F.avg_pool2d(x, 2, 2)
        x = x.view(-1, 128*4)
        x = self.last(x)
        self.act['last']=x
        return F.log_softmax(x, dim=1),x


########--------------------------------------------Main Function --------------------------------##################
def main():
    # Training settings
    parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
    parser.add_argument('--batch-size', type=int, default=128, metavar='N',
                        help='input batch size for training (default: 128)')
    parser.add_argument('--test-batch-size', type=int, default=1000, metavar='N',
                        help='input batch size for testing (default: 1000)')
    parser.add_argument('--train_epoch', type=int, default=10, metavar='N',
                        help='number of epochs for train step (default: 10)')
    parser.add_argument('--lr', type=float, default=0.001, metavar='LR',
                        help='learning rate (default: 0.001)')
    parser.add_argument('--momentum', type=float, default=0.9, metavar='M',
                        help='SGD momentum (default: 0.9)')
    parser.add_argument('--no-cuda', action='store_true', default=False,
                        help='disables CUDA training')
    parser.add_argument('--seed', type=int, default=1, metavar='S',
                        help='random seed (default: 1)')
    parser.add_argument('--log-interval', type=int, default=20, metavar='N',
                        help='how many batches to wait before logging training status')
    parser.add_argument('--full_task', type=int, default=0, metavar='N',
                        help='If full dataset is to be simulated (default: 0)')
    parser.add_argument('--call_test', type=int, default=0, metavar='N',
                            help='if 1 calls masked test (default: 0)')
    parser.add_argument('--split', type=int, default=0, metavar='N',
                        help='Split task ID; 0: for first task; 1: for 2nd task, 4: for 5th task (default: 0)')
    parser.add_argument('--train', type=int, default=1, metavar='N',
                        help='If 1 trains the model else loads (default: 1)')
    parser.add_argument('--retrain', type=int, default=1, metavar='N',
                        help='If 1 retrains the model with PCA compression (default: 1)')
    parser.add_argument('--classifier_finetune', type=int, default=1, metavar='N',
                        help='If 1 finetunes classifier for the next task (default: 1)')
    parser.add_argument('--finetune_epoch', type=int, default=10, metavar='N',
                        help='Specify the classifer finetune epochs')
    parser.add_argument('--save-model', type=int, default=0, metavar='N',
                        help='For Saving the current Model: 1==save')
    parser.add_argument('--param_dir', default='CIFAR10_task', type=str,   
                        help='Pre-trained weights directory')
    # parser.add_argument('--file_suffix', type=int, default=1, metavar='N',
    #                     # help='adds suffix to file name')
    parser.add_argument('--num_out', type=int, default=2, metavar='N',
                        help='Number of output units for this task (default: 2)')
    parser.add_argument('--var_kept', type=float, default=0.995, metavar='VK',
                        help='percentage of PCA variance kept during training (default: 99.5%)')
    parser.add_argument('--finetune_pca',  default=False, action='store_true', help='dont tune after PCA')
    parser.add_argument('--add_pca',  default=False, action='store_true', help='dont tune after PCA')
    parser.add_argument('--zero_out_others',  default=False, action='store_true', help='dont tune after PCA')    
    parser.add_argument('--file_suffix', dest='file_suffix', default='default', type=str,
                        help="Exp name to be added to the suffix")
    # parser.add_argument('--', type=float, default=0.995, metavar='VK',
    #                     help='percentage of PCA variance kept during training (default: 99.5%)')

    parser.add_argument('--epoch_list', nargs='+', type=int)
    args = parser.parse_args()
    print (args)
    
    # model directories 
    model_root     = os.path.expanduser('PARAM/'+args.param_dir)
    running_param_fname   = os.path.join(model_root, 'cifar10_rp_CT{}.pth'.format(args.file_suffix)) # CT stands for Classifer training 
    param_fnameB   = os.path.join(model_root, 'cifar10_multi_CT{}.pth'.format(args.file_suffix))
    param_fnameB_rt= os.path.join(model_root, 'cifar10_multi_CT{}_rt.pth'.format(args.file_suffix))

    # seeds and device setup 
    use_cuda = not args.no_cuda and torch.cuda.is_available()
#    logger = Logger('./logs')
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if use_cuda else "cpu")
    kwargs = {'num_workers': 3, 'pin_memory': True} if use_cuda else {}
    
 ########-------------------------------------------- Train dataset --------------------------------##################
    taskA=[];taskB=[];taskC=[];taskD=[];taskE=[]
    test_taskA=[];test_taskB=[];test_taskC=[];test_taskD=[];test_taskE=[]
    
    train_dataset= datasets.CIFAR10(root='./data', train=True, download=True,transform=transforms.Compose([
                            transforms.ToTensor(),
                            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))]))
    
    if (args.train==1 and args.full_task==1):
        train_loader = torch.utils.data.DataLoader(train_dataset,batch_size=args.batch_size, shuffle=True, **kwargs)
    else:    
        for batch_id, (inputs,labels) in enumerate (train_dataset):
            if labels < 2:
                taskA.append((inputs,labels))
            elif labels>=2 and labels<4:
                taskB.append((inputs,labels))
            elif labels>=4 and labels<6:
                taskC.append((inputs,labels))
            elif labels>=6 and labels<8:
                taskD.append((inputs,labels))
            elif labels>=8 and labels<10:
                taskE.append((inputs,labels))
        
        train_task =[taskA,taskB,taskC,taskD,taskE]
        
########-------------------------------------------- Test dataset --------------------------------##################   
    test_dataset= datasets.CIFAR10(root='./data', train=False, transform=transforms.Compose([
                           transforms.ToTensor(),
                           transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))]))
    if (args.full_task==1):
        test_loader = torch.utils.data.DataLoader(test_dataset,batch_size=args.test_batch_size, shuffle=True, **kwargs)
    else:
        for batch_id, (inputs,labels) in enumerate (test_dataset):
            if labels < 2:
                test_taskA.append((inputs,labels))
            elif labels>=2 and labels<4:
                test_taskB.append((inputs,labels))
            elif labels>=4 and labels<6:
                test_taskC.append((inputs,labels))
            elif labels>=6 and labels<8:
                test_taskD.append((inputs,labels))
            elif labels>=8 and labels<10:
                test_taskE.append((inputs,labels))
        
        test_task =[test_taskA,test_taskB,test_taskC,test_taskD,test_taskE]
    
    classes = ('plane', 'car', 'bird', 'cat','deer', 'dog', 'frog', 'horse', 'ship', 'truck')

########-------------------------------------------- Model and Optimaizer --------------------------------################## 
    model   = Net().to(device)
    oldmodel= Net().to(device) # creating a model for network initialization purpose 
    print(model)
    # creating lists to save network accuracies 
    accuracy_train =[]
    accuracy_retrain =[]
    writer = SummaryWriter(log_dir="runs/" + args.file_suffix)

    for idx in range (1):
        #args.split = input('specify args.split:')
        args.split = idx 
        print('Classifing {}-{} | Task id-{}'.format(args.num_out*args.split,args.num_out*(args.split+1)-1,idx+1))
        print('Loading split CIFAR10 train task {}...'.format(args.split+1))
        train_loader = torch.utils.data.DataLoader(train_task[args.split],batch_size=args.batch_size, shuffle=True, **kwargs) ## train_task name  
        train_loader_sudo = torch.utils.data.DataLoader(train_task[args.split],batch_size=5000, shuffle=True, **kwargs)
        print('Loading split CIFAR10 test task {}...'.format(args.split+1))
        test_loader = torch.utils.data.DataLoader(test_task[args.split],batch_size=5000, shuffle=True, **kwargs) ## test_task name
                
    #######--------------------------------------------------train------------------------------------###################      
        if (args.train ==1):            
            if args.split > 0 :
                ## Loading model from already learned tasks 
                if (args.split>1):
                    args.lr = 0.001
                    args.train_epoch = 50
                    args.epoch_list = [15,20,30,40,55]
                else:
                    args.lr = 0.01
                model_param = torch.load(param_fnameB_rt) #...............Load model of T-1 task
                model.load_state_dict(model_param['state_dict'])
                
                running_param = torch.load(running_param_fname) # load running filter and class Weight and bias
                keep_classifier_list = running_param['classifier_list']
                opt_filter_list = running_param['opt_filter_list']
                lx= opt_filter_list[args.split-1] ## this is an array
                filter_num = [lx[0],lx[0],lx[1],lx[1],lx[2],lx[2],lx[3],lx[3],lx[4],lx[4]]
            
            else:
                args.lr = 0.01
                print('Traning from the scratch model with learning rate:',args.lr)
                keep_classifier_list = []
                opt_filter_list = []
                filter_num =[]
            
            print('Starting learning rate for Training task {} is {}'.format(idx+1,args.lr))
            optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum) # using SGD with momentum
            loss_hist=[]
            loss_test=[]
            for epoch in range(1, args.train_epoch + 1): 
                if (args.split<2 and (epoch == 20 or epoch == 35) ):                
                    adjust_learning_rate(optimizer, epoch, args) 
                elif (args.split > 1 and epoch == int(args.train_epoch*0.9)):
                    adjust_learning_rate(optimizer, epoch, args) 
                # logger removed
                loss_hist=train_next(args, model, device, train_loader, optimizer, epoch,loss_hist,filter_num)
                loss_test, acc =test(args, model, device, test_loader,loss_test)

            ## Saving the test accuracies in the list 
            acc=test_acc_save(args, model, device, test_loader,loss_test)
            accuracy_train.append(acc)
            if (args.save_model):
                if (args.split ==0):
                    model_param_train = {'state_dict': model.state_dict() } 
                else:
                    model_param_train  = {'state_dict': model.state_dict(), 'pca_comp_final': model_param['pca_comp_final'],'sing_val': model_param['sing_val']}
                print('Saving base Model after TRAINING...')
                torch.save(model_param_train,param_fnameB)   
        
        if (args.call_test ==1):
            ''' This part of the code test the trained model with task hint 
            e.g. if idx=1 then this is 2nd task and calling this part will return the 
            test accuracy for the incrementally learned 2nd task'''
            sudo=[]
            running_param = torch.load(running_param_fname)
            keep_classifier_list = running_param['classifier_list']
            opt_filter_list = running_param['opt_filter_list']
            
            model_param = torch.load(param_fnameB_rt) #...............Load model
            model.load_state_dict(model_param['state_dict'])
            
            test_masked_model= Net().to(device) 
            test_masked_model.load_state_dict(model_param['state_dict'])
            print('Accuracy real is')
            call_test_model (model,test_masked_model, args , device, test_loader, sudo, opt_filter_list[args.split],keep_classifier_list,idx) 
        
        optimal_num_filters = np.zeros(5)
        pca_comp_final=[]
        singular_values=[]            
        ############----------------------------------------Re-train------------------------------------###################  
        
        if (args.retrain == 1): 
            sudo=[]
            loss_hist=[]
            loss_test=[]

            args.lr = 0.001
            
            if (args.train == 0) :
                model_param = torch.load(param_fnameB) #...............Load taskA model after training 
                model.load_state_dict(model_param['state_dict'])
                
                if (args.split > 0):
                    running_param = torch.load(running_param_fname)# load running filter and class Weight and bias
                    keep_classifier_list = running_param['classifier_list']
                    opt_filter_list = running_param['opt_filter_list']
                    lx= opt_filter_list[args.split-1] ## this is an array
                    filter_num = [lx[0],lx[0],lx[1],lx[1],lx[2],lx[2],lx[3],lx[3],lx[4],lx[4]]
                    
                elif args.split ==0:
                    keep_classifier_list = []
                    opt_filter_list = []
                    filter_num =[]

            params = {n: p for n, p in model.named_parameters()}
            pca_weights = {}
            pca_opt_num  = {}
            
            for n, p in params.items(): 
                if 'weight' in n and 'last' not in n :
                    out_size = model.state_dict()[n].size(0)
                    print('Test accuracy before even PCA compression' ) 
        

                    #########------------------------------------- Run PCA ------------------------------------############
                
                    print ('Collecting activation for PCA Compression at layer' ,  n)
                    #collecting activation for PCA

                    # import pdb; pdb.set_trace()
                    # loaded activations
                    test(args, model, device, train_loader_sudo,sudo) 

                    # specify the amount of PCA variance kept  
                    t = args.var_kept 
                    name_key = n.split('.')[0]
                    optimal_num_filters, pca = run_PCA(model.act[name_key],0,out_size,threshold=t) 
                    pca_weights[n] = np.transpose(pca.components_)
                    pca_weights[name_key + '.bias'] = np.transpose(pca.components_)
                    pca_opt_num[n] = optimal_num_filters
                    pca_opt_num[name_key + '.bias'] = optimal_num_filters


            
            model_param = {'state_dict': model.state_dict(), 'pca_weights': pca_weights, 'pca_opt_num': pca_opt_num}  
        model_root  = os.path.expanduser('PARAM/'+args.param_dir)
        print(model_param['pca_opt_num'])
        torch.save(model_param,os.path.join(model_root, 'baseline_new.pth'))
        # test
        # pca_final_ = {}
        # import pdb; pdb.set_trace()

        # for n, p in params.items():
             
        # import pdb; pdb.set_trace()


            # # save and print the model statistics 
            # model_param = {'state_dict': model.state_dict(), 'pca_comp_final': pca_comp_final,'sing_val': singular_values}
            # if (args.save_model):
            #     print('Saving Model...')
            #     torch.save(model_param,param_fnameB_rt)
            #     torch.save(running_param,running_param_fname)
            # print ('Training Accuracy:',accuracy_train)
            # print ('Retraining Accuracy:',accuracy_retrain)
            # print ('Opt_filter_list:',opt_filter_list)















                
            #     #########------------------------------------- Retraining after PCA ------------------------------------############
            #     optim_list = [  {'params': model.conv1.parameters()},
            #                     {'params': model.conv2.parameters()},
            #                     {'params': model.conv3.parameters()},
            #                     {'params': model.conv4.parameters()},
            #                     {'params': model.conv5.parameters()},                                          
            #                     {'params': model.fc1.parameters()}]


            #     # print('Test accuracy before finetuning' )
            #     # loss_test=test(args, model, device, test_loader,loss_test) 
            #     optimizer = optim.SGD(optim_list, lr=args.lr, momentum=args.momentum) # using SGD with momentum 
            #     if args.finetune_pca:
            #         for epoch in range(1, args.epoch_list[i] + 1):   
            #             if ( epoch == int(args.epoch_list[i]*0.9) ):
            #             	adjust_learning_rate(optimizer,epoch,args)
            #             layer=i       
            #             loss_hist=train_next_pca(args, model, device, train_loader, optimizer, epoch,layer,loss_hist,optimal_num_filters, filter_num)
            

            # ##--------------------------------------------------------Saving --------------------------------------------------------## 
            # # saving test accuracy after retraining 
            
        
                  
if __name__ == '__main__':
    main()
