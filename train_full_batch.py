import torch
import torch.nn as nn
import numpy as np
from torch.nn import Parameter
import torch.optim as optim
from sklearn import metrics
import random
import os
import sys
import utils
from tqdm import tqdm
import time
import argparse
import dgl
from scipy.sparse import csr_matrix
from scipy.sparse import vstack as s_vstack
from sklearn.preprocessing import StandardScaler
from gensim.models import Word2Vec
import multiprocessing
from concurrent.futures import as_completed
from concurrent.futures import ProcessPoolExecutor
from scipy.sparse import csr_matrix, lil_matrix, csc_matrix

from preprocess.data_load import gen_DGLGraph, gen_weighted_DGLGraph, gen_sampleweighted_DGLGraph
from preprocess.data_load import CustomMultiLayerNeighborSampler
import preprocess.data_load as dl
from preprocess.batch import DataLoader, DataLoaderwRank
from initialize.initial_embedder import MultipleEmbedding
from initialize.random_walk_hyper import random_walk_hyper

from model.HNHN import HNHN
from model.HGNN import HGNN
from model.GAT import GAT
from model.HAT import HyperAttn
from model.UniGCN import UniGCNII
from model.HCHA import HCHA
from model.Transformer import Transformer, TransformerLayer
from model.layer import FC, ScorerTransformer, Wrap_Embedding
from model.RNN import ScorerGRU


# Make Output Directory --------------------------------------------------------------------
initialization = "rw"
args = utils.parse_args()

assert args.embedder == "hcha"
assert args.scorer == "sm"
assert args.bs == -1

if args.evaltype == "test":
    assert args.fix_seed
    outputdir = "results_test/" + args.dataset_name + "_" + str(args.k) + "/" + initialization + "/"
    outputParamResFname = outputdir + args.model_name + "/param_result.txt"
    outputdir += args.model_name + "/" + args.param_name +"/" + str(args.seed) + "/"
else:
    outputdir = "results/" + args.dataset_name + "_" + str(args.k) + "/" + initialization + "/"
    outputParamResFname = outputdir + args.model_name + "/param_result.txt"
    outputdir += args.model_name + "/" + args.param_name +"/"
if os.path.isdir(outputdir) is False:
    os.makedirs(outputdir)
if os.path.isfile(outputParamResFname) is False:
    with open(outputParamResFname, "w") as f:
        f.write("parameter,TrainLoss,TrainAcc,ValidAcc\n")
print("OutputDir = " + outputdir)
print("Output Param Result = " + outputParamResFname)

if os.path.isdir(outputdir) is False:
    os.makedirs(outputdir)
    
# Initialization --------------------------------------------------------------------
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
dataset_name = args.dataset_name #'citeseer' 'cora'

if args.fix_seed:
    random.seed(args.seed)
    np.random.seed(args.seed)
    dgl.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    dgl.seed(args.seed)

exp_num = args.exp_num
test_epoch = args.test_epoch
plot_epoch = args.epochs

patience = 0
best_eval_acc = 0

# Check Exist -----------------------------------------------------------------------
# Check Exist -----------------------------------------------------------------------
existflag = False
run_only_test = False
if args.recalculate is False:
    if os.path.isfile(outputdir + "log_valid_micro.txt"):
        max_acc = 0
        cur_patience = 0
        epoch = 0
        with open(outputdir + "log_valid_micro.txt", "r") as f:
            for line in f.readlines():
                ep_str = line.rstrip().split(":")[0].split(" ")[0]
                acc_str = line.rstrip().split(":")[-1]
                epoch = int(ep_str)
                if max_acc < float(acc_str):
                    cur_patience = 0
                    max_acc = float(acc_str)
                else:
                    cur_patience += 1
                if cur_patience > args.patience:
                    break
        if cur_patience > args.patience or epoch == args.epochs:
            existflag = True
        
        if args.evaltype == "test":
            if os.path.isfile(outputdir + "log_test_micro.txt") is False:
                if os.path.isfile(outputdir + "initembedder.pt") is False:
                    existflag = False
                elif os.path.isfile(outputdir + "embedder.pt") is False:
                    existflag = False
                elif os.path.isfile(outputdir + "scorer.pt") is False:
                    existflag = False
                else:
                    run_only_test = True
            elif os.path.isfile(outputdir + "evaluation.txt") is False:
                if os.path.isfile(outputdir + "initembedder.pt") is False:
                    existflag = False
                elif os.path.isfile(outputdir + "embedder.pt") is False:
                    existflag = False
                elif os.path.isfile(outputdir + "scorer.pt") is False:
                    existflag = False
                else:
                    run_only_test = True
        if existflag and (run_only_test is False):
            sys.exit("Already Run by log valid micro txt")
    elif args.evaltype == "valid" and os.path.isfile(outputdir + "log_test_micro.txt"):
        max_acc = 0
        cur_patience = 0
        epoch = 0
        with open(outputdir + "log_test_micro.txt", "r") as f:
            for line in f.readlines():
                ep_str = line.rstrip().split(":")[0].split(" ")[0]
                acc_str = line.rstrip().split(":")[-1]
                epoch = int(ep_str)
                if max_acc < float(acc_str):
                    cur_patience = 0
                    max_acc = float(acc_str)
                else:
                    cur_patience += 1
                if cur_patience > args.patience:
                    break
        if cur_patience > args.patience or epoch == args.epochs:
            existflag = True
        if existflag:
            sys.exit("Already Run by log test micro txt")
            
if args.check:
    with open("./run/notyet.txt", "+a") as f:
        f.write(outputdir + "\n")
    sys.exit("**Not Yet**")

if run_only_test:
    if os.path.isfile(outputdir + "log_test_micro.txt"):
        os.remove(outputdir + "log_test_micro.txt")
    if os.path.isfile(outputdir + "log_test_confusion.txt"):
        os.remove(outputdir + "log_test_confusion.txt")
    if os.path.isfile(outputdir + "log_test_macro.txt"):
        os.remove(outputdir + "log_test_macro.txt")
elif os.path.isfile(outputdir + "checkpoint.pt"):
    print("Start from checkpoint")
else:
    if os.path.isfile(outputdir + "log_train.txt"):
        os.remove(outputdir + "log_train.txt")
    if os.path.isfile(outputdir + "log_valid_micro.txt"):
        os.remove(outputdir + "log_valid_micro.txt")
    if os.path.isfile(outputdir + "log_valid_confusion.txt"):
        os.remove(outputdir + "log_valid_confusion.txt")
    if os.path.isfile(outputdir + "log_valid_macro.txt"):
        os.remove(outputdir + "log_valid_macro.txt")
    if os.path.isfile(outputdir + "log_test_micro.txt"):
        os.remove(outputdir + "log_test_micro.txt")
    if os.path.isfile(outputdir + "log_test_confusion.txt"):
        os.remove(outputdir + "log_test_confusion.txt")
    if os.path.isfile(outputdir + "log_test_macro.txt"):
        os.remove(outputdir + "log_test_macro.txt")

# Data -----------------------------------------------------------------------------
# Revised
data = dl.Hypergraph(args, dataset_name)
data.split_data(args.val_ratio, args.test_ratio)
train_data = data.get_data(0)
valid_data = data.get_data(1)
test_data = data.get_data(2)

train_edata, train_vdata, train_label = [], [], []
valid_edata, valid_vdata, valid_label = [], [], []
test_edata, test_vdata, test_label = [], [], []
for hedge in train_data:
    for vidx, v in enumerate(data.hedge2node[hedge]):
        train_edata.append(hedge)
        train_vdata.append(v)
        train_label.append(data.hedge2nodepos[hedge][vidx])
for hedge in valid_data:
    for vidx, v in enumerate(data.hedge2node[hedge]):
        valid_edata.append(hedge)
        valid_vdata.append(v)
        valid_label.append(data.hedge2nodepos[hedge][vidx])
for hedge in test_data:
    for vidx, v in enumerate(data.hedge2node[hedge]):
        test_edata.append(hedge)
        test_vdata.append(v)
        test_label.append(data.hedge2nodepos[hedge][vidx])

train_label = torch.LongTensor(train_label).to(device)
valid_label = torch.LongTensor(valid_label).to(device)
test_label = torch.LongTensor(test_label).to(device)
args.input_vdim = data.v_feat.size(1)
args.input_edim = data.e_feat.size(1)
g = gen_DGLGraph(args, data.hedge2node, data.hedge2nodepos, data.node2hedge, device).to(device)

# init embedder
args.input_vdim = 48
args.input_edim = 48
savefname = "../%s_%d_wv_%d_%s.npy" % (args.dataset_name, args.k, args.input_vdim, args.walk)
node_list = np.arange(data.numnodes).astype('int')
if os.path.isfile(savefname) is False:
    walk_path = random_walk_hyper(args, node_list, data.hedge2node)
    walks = np.loadtxt(walk_path, delimiter=" ").astype('int')
    print("Start turning path to strs")
    split_num = 20
    pool = ProcessPoolExecutor(max_workers=split_num)
    process_list = []
    walks = np.array_split(walks, split_num)
    result = []
    for walk in walks:
        process_list.append(pool.submit(utils.walkpath2str, walk))
    for p in as_completed(process_list):
        result += p.result()
    pool.shutdown(wait=True)
    walks = result
    # print(walks)
    print("Start Word2vec")
    print("num cpu cores", multiprocessing.cpu_count())
    w2v = Word2Vec( walks, vector_size=args.input_vdim, window=10, min_count=0, sg=1, epochs=1, workers=multiprocessing.cpu_count())
    print(w2v.wv['0'])
    wv = w2v.wv
    A = [wv[str(i)] for i in range(data.numnodes)]
    np.save(savefname, A)
else:
    print("load exist init walks")
    A = np.load(savefname)
A = StandardScaler().fit_transform(A)
# A = np.concatenate(
#     (np.zeros((1, A.shape[-1]), dtype='float32'), A), axis=0)
A = A.astype('float32')
A = torch.tensor(A).to(device)
initembedder = Wrap_Embedding(data.numnodes, args.input_vdim, scale_grad_by_freq=False, padding_idx=0, sparse=False)
initembedder.weight = nn.Parameter(A)
# Randomwalk_Word2vec = Word2vec_Skipgram(dict_size=int(data.numnodes + 1), embedding_dim=48,
#                                         window_size=10, u_embedding=node_embedding,
#                                         sparse=False).to(device)

print("Model:", args.embedder)
# model init - Only HCHA
embedder = HCHA(args.input_vdim, args.input_edim, args.dim_hidden, args.dim_vertex, args.dim_edge, num_layers=args.num_layers, num_heads=args.num_heads, feat_drop=args.dropout).to(device)

print("Scorer = ", args.scorer)
# pick scorer - Only 1-layer Linear
scorer = FC(args.dim_vertex + args.dim_edge, args.dim_hidden, args.output_dim, args.scorer_num_layers, args.dropout).to(device)

# pick optimizer
if args.optimizer == "adam":
    optim = torch.optim.Adam(list(initembedder.parameters())+list(embedder.parameters())+list(scorer.parameters()), lr=args.lr) #, weight_decay=args.weight_decay)
elif args.optimizer == "adamw":
    optim = torch.optim.AdamW(list(initembedder.parameters())+list(embedder.parameters())+list(scorer.parameters()), lr=args.lr)
elif args.optimizer == "rms":
    optime = torch.optim.RMSprop(list(initembedder.parameters())+list(embedder.parameters())+list(scorer.parameters()), lr=args.lr)
scheduler = torch.optim.lr_scheduler.ExponentialLR(optim, gamma=args.gamma)
loss_fn = nn.CrossEntropyLoss()

# Train =================================================================================================================================================================================
total_step = 0
train_acc=0
print(A.shape)
print(data.numnodes)
nodes = torch.LongTensor(range(data.numnodes)).to(device)
for epoch in tqdm(range(1, args.epochs + 1), desc='Epoch'): # tqdm
    # Training stage
    embedder.train()
    scorer.train()
    # print(torch.LongTensor(range(data.numnodes - 1)))
    v_feat, recon_loss = initembedder(nodes)
    e_feat = torch.zeros((data.numhedges, args.input_vdim)).to(device)
    DV2 = data.DV2.to(device)
    invDE = data.invDE.to(device)
    v, e = embedder(g, v_feat, e_feat, DV2, invDE)

    # Predict Class    
    hembedding = e[train_edata]
    vembedding = v[train_vdata]
    input_embeddings = torch.cat([hembedding,vembedding], dim=1)
    predictions = scorer(input_embeddings)
    
    # Back Propagation
    train_ce_loss = loss_fn(predictions, train_label)
    train_loss = train_ce_loss + args.rw * recon_loss
    optim.zero_grad()
    train_loss.backward() # retain_graph=True
    optim.step()
    scheduler.step()
    torch.cuda.empty_cache()
    
    # Calculate Accuracy & Epoch Loss
    pred_cls = torch.argmax(predictions, dim=1)
    train_acc = torch.eq(pred_cls, train_label).sum().item() / len(train_label)
    print("%d epoch: Training loss : %.4f (%.4f, %.4f) / Training acc : %.4f\n" % (epoch, train_loss, train_ce_loss, recon_loss, train_acc))
    with open(outputdir + "log_train.txt", "+a") as f:
        f.write("%d epoch: Training loss : %.4f (%.4f, %.4f) / Training acc : %.4f\n" % (epoch, train_loss, train_ce_loss, recon_loss, train_acc))
        
    # Test
    if epoch % test_epoch == 0:
        embedder.eval()
        scorer.eval()
        
        hembedding = e[valid_edata]
        vembedding = v[valid_vdata]
        input_embeddings = torch.cat([hembedding,vembedding], dim=1)
        predictions = scorer(input_embeddings)
        eval_ce_loss = loss_fn(predictions, valid_label)
        eval_loss = eval_ce_loss + args.rw * recon_loss
        predictions = scorer(input_embeddings)
        pred_cls = torch.argmax(predictions, dim=1)
        eval_acc = torch.eq(pred_cls, valid_label).sum().item() / len(valid_label)
        
        y_test = valid_label.detach().cpu().numpy()
        pred = pred_cls.detach().cpu().numpy()
        
        confusion, accuracy, precision, recall, f1 = utils.get_clf_eval(y_test, pred, avg='micro')
        with open(outputdir + "log_valid_micro.txt", "+a") as f:
            f.write("{} epoch:Test Loss:{} ({}, {})/Accuracy:{}/Precision:{}/Recall:{}/F1:{}\n".format(epoch, eval_loss, eval_ce_loss, recon_loss, eval_acc, precision, recall, f1))
        confusion, accuracy, precision, recall, f1 = utils.get_clf_eval(y_test, pred, avg='macro')
        with open(outputdir + "log_valid_confusion.txt", "+a") as f:
            for r in range(args.output_dim):
                for c in range(args.output_dim):
                    f.write(str(confusion[r][c]))
                    if c == (args.output_dim - 1):
                        f.write("\n")
                    else:
                        f.write("\t")
        with open(outputdir + "log_valid_macro.txt", "+a") as f:               
            f.write("{} epoch:Test Loss:{} ({}, {})/Accuracy:{}/Precision:{}/Recall:{}/F1:{}\n".format(epoch, eval_loss, eval_ce_loss, recon_loss, accuracy,precision,recall,f1))

        if best_eval_acc < eval_acc:
            print(best_eval_acc)
            best_eval_acc = eval_acc
            patience = 0
            if args.evaltype == "test" or args.save_epochs > 0:
                print("Model Save")
                modelsavename = outputdir + "embedder.pt"
                torch.save(embedder.state_dict(), modelsavename)
                scorersavename = outputdir + "scorer.pt"
                torch.save(scorer.state_dict(), scorersavename)
                initembeddersavename = outputdir + "initembedder.pt"
                torch.save(initembedder.state_dict(),initembeddersavename)
        else:
            patience += 1

        if patience > args.patience:
            break

nodes = torch.LongTensor(range(data.numnodes)).to(device)
if args.evaltype == "test":
    initembedder.load_state_dict(torch.load(outputdir + "initembedder.pt")) # , map_location=device
    embedder.load_state_dict(torch.load(outputdir + "embedder.pt")) # , map_location=device
    scorer.load_state_dict(torch.load(outputdir + "scorer.pt")) # , map_location=device
    
    initembedder.eval()
    embedder.eval()
    scorer.eval()

    with torch.no_grad():
        v_feat, recon_loss = initembedder(nodes)
        e_feat = torch.zeros((data.numhedges, args.input_vdim)).to(device)
        DV2 = data.DV2.to(device)
        invDE = data.invDE.to(device)
        v, e = embedder(g, v_feat, e_feat, DV2, invDE)
        
        hembedding = e[test_edata]
        vembedding = v[test_vdata]
        input_embeddings = torch.cat([hembedding,vembedding], dim=1)
        predictions = scorer(input_embeddings)
        eval_ce_loss = loss_fn(predictions, test_label)
        eval_loss = eval_ce_loss + args.rw * recon_loss
        pred_cls = torch.argmax(predictions, dim=1)
        eval_acc = torch.eq(pred_cls, test_label).sum().item() / len(test_label)
        
        y_test = test_label.detach().cpu().numpy()
        pred = pred_cls.detach().cpu().numpy()
        
        confusion, accuracy, precision, recall, f1 = utils.get_clf_eval(y_test, pred, avg='micro')
        with open(outputdir + "log_test_micro.txt", "+a") as f:
            f.write("{} epoch:Test Loss:{} ({}, {})/Accuracy:{}/Precision:{}/Recall:{}/F1:{}\n".format(epoch, eval_loss, eval_ce_loss, recon_loss, eval_acc, precision, recall, f1))
        confusion, accuracy, precision, recall, f1 = utils.get_clf_eval(y_test, pred, avg='macro')
        with open(outputdir + "log_test_confusion.txt", "+a") as f:
            for r in range(args.output_dim):
                for c in range(args.output_dim):
                    f.write(str(confusion[r][c]))
                    if c == (args.output_dim - 1):
                        f.write("\n")
                    else:
                        f.write("\t")
        with open(outputdir + "log_test_macro.txt", "+a") as f:               
            f.write("{} epoch:Test Loss:{} ({}, {})/Accuracy:{}/Precision:{}/Recall:{}/F1:{}\n".format(epoch, eval_loss, eval_ce_loss, recon_loss, accuracy,precision,recall,f1))
        
        

