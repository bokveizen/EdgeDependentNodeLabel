import torch
import torch.nn as nn
import numpy as np
import torch.nn.functional as F
import pdb
import math
import os
import time

# Based on SetTransformer https://github.com/juho-lee/set_transformer

class MAB(nn.Module):
    def __init__(self, dim_Q, dim_K, dim_V, num_heads, ln=False, numlayers=1, RE="None"):
        super(MAB, self).__init__()
        self.dim_V = dim_V
        self.num_heads = num_heads
        self.fc_q = nn.Linear(dim_Q, dim_V)
        self.fc_k = nn.Linear(dim_K, dim_V)
        self.fc_v = nn.Linear(dim_K, dim_V)
        if ln:
            self.ln0 = nn.LayerNorm(dim_V)
            self.ln1 = nn.LayerNorm(dim_V)
        self.numlayers = numlayers
        self.fc_o = nn.ModuleList()
        for _ in range(numlayers):
            self.fc_o.append(nn.Linear(dim_V, dim_V))
        self.RE = RE
        if self.RE == "ShawRE":
            self.kp = nn.Parameter(torch.Tensor(1, dim_V // self.num_heads))
            self.vp = nn.Parameter(torch.Tensor(1, dim_V // self.num_heads))
            torch.nn.init.xavier_uniform_(self.kp)
            torch.nn.init.xavier_uniform_(self.vp)
            
#         elif self.RE == "RafRE":
#             self.s = nn.Parameter(torch.empty(1,1))
#             torch.nn.init.xavier_uniform_(self.s)
        #self.fc_o = nn.Linear(dim_V, dim_V)
        
    def forward(self, Q, K, Kpos=None):
        Q = self.fc_q(Q)
        K, V = self.fc_k(K), self.fc_v(K)
        
        dim_split = self.dim_V // self.num_heads
        Q_ = torch.cat(Q.split(dim_split, 2), 0)
        K_ = torch.cat(K.split(dim_split, 2), 0)
        V_ = torch.cat(V.split(dim_split, 2), 0)
        if Kpos is not None:
            Kpos_ = torch.cat([Kpos for _ in range(self.num_heads)], 0)
        
        if self.RE == "ITRE":
            A = torch.softmax( (torch.matmul(Q_, torch.transpose(K_, 1, 2)) / math.sqrt(self.dim_V)) + torch.log(Kpos_), 2)
            O = torch.cat((Q_ + torch.matmul(A, V_)).split(Q.size(0), 0), 2)
        elif self.RE == "ShawRE":
            dim0, dim1 = Q_.shape[0], Q_.shape[1]
            numv = V_.shape[1]
            KE = torch.bmm(Q_.unsqueeze(2).view(-1, 1, dim_split) , torch.transpose(torch.matmul(Kpos_.unsqueeze(-1), self.kp), 2, 3).view(-1,dim_split, numv))
            KE = KE.view(dim0, dim1, -1)
            A = torch.softmax( (torch.matmul(Q_, torch.transpose(K_, 1, 2)) / math.sqrt(self.dim_V)) + KE, 2)
            VE = torch.bmm(A.view(-1, numv).unsqueeze(1), torch.matmul(Kpos_.unsqueeze(-1), self.vp).view(-1, numv, dim_split))
            VE = VE.view(dim0, dim1, -1)
            V = torch.matmul(A, V_) + VE
            O = torch.cat((Q_ + V).split(Q.size(0), 0), 2)            
        #elif self.RE == "RafRE":
        #    A = torch.softmax( (torch.matmul(Q_, torch.transpose(K_, 1, 2)) / math.sqrt(self.dim_V), 2) + self.s * Kpos )
        else:
            A = torch.softmax(torch.matmul(Q_, torch.transpose(K_, 1, 2)) / math.sqrt(self.dim_V), 2)
            O = torch.cat((Q_ + torch.matmul(A, V_)).split(Q.size(0), 0), 2)
        # O = torch.cat((Q_ + torch.matmul(A, K_)).split(Q.size(0), 0), 2)
        O = O if getattr(self, 'ln0', None) is None else self.ln0(O)
        resO = O
        for i, lin in enumerate(self.fc_o[:-1]):
            O = F.relu(lin(O), inplace=True)
        O = resO + F.relu(self.fc_o[-1](O))
        O = O if getattr(self, 'ln1', None) is None else self.ln1(O)
        return O

class SAB(nn.Module):
    def __init__(self, dim_in, dim_out, num_heads, ln=False):
        super(SAB, self).__init__()
        self.mab = MAB(dim_in, dim_in, dim_out, num_heads, ln=ln)
    def forward(self, X):
        out = self.mab(X, X)
        return out
    
class IMAB(nn.Module):
    def __init__(self, dim_Q, dim_K, dim_V, num_heads, num_inds, ln=False):
        super(IMAB, self).__init__()
        # X is dim_in, I is (num_inds) * (dim_out)
        # After mab0, I is represented by X => H = (num_inds) * (dim_out)
        # After mab1, X is represented by H => X' = (X.size[1]) * (dim_in)
        self.I = nn.Parameter(torch.Tensor(1, num_inds, dim_V))
        nn.init.xavier_uniform_(self.I)
        self.mab0 = MAB(dim_V, dim_K, dim_V, num_heads, ln=ln)
        self.mab1 = MAB(dim_Q, dim_V, dim_V, num_heads, ln=ln)

    def forward(self, Q, K):
        # Q, K
        H = self.mab0(self.I.repeat(K.size(0), 1, 1), K)
        return self.mab1(Q, H)

class ISAB(nn.Module):
    def __init__(self, dim_in, dim_out, num_heads, num_inds, ln=False, RE="None", pos_dim=0):
        super(ISAB, self).__init__()
        self.RE = RE
        # X is dim_in, I is (num_inds) * (dim_out)
        # After mab0, I is represented by X => H = (num_inds) * (dim_out)
        # After mab1, X is represented by H => X' = (X.size[1]) * (dim_in)
        self.I = nn.Parameter(torch.Tensor(1, num_inds, dim_out))
        nn.init.xavier_uniform_(self.I)
        if pos_dim > 0:
            self.relation_I = nn.Parameter(torch.Tensor(pos_dim, num_inds))
            nn.init.xavier_uniform_(self.relation_I)
        self.mab0 = MAB(dim_out, dim_in, dim_out, num_heads, ln=ln, RE=RE)
        self.mab1 = MAB(dim_in, dim_out, dim_out, num_heads, ln=ln, RE=RE)

    def forward(self, X, Xpos=None):
        if Xpos is not None:
            Xpos = torch.matmul(Xpos,self.relation_I)
            H = self.mab0(self.I.repeat(X.size(0), 1, 1), X, torch.transpose(Xpos,1,2))
        else:
            H = self.mab0(self.I.repeat(X.size(0), 1, 1), X, Xpos)
        return self.mab1(X, H, Xpos)

class PMA(nn.Module):
    def __init__(self, dim_in, dim_out, num_heads, num_seeds, ln=False, numlayers=1):
        # (num_seeds, dim) is represented by X
        super(PMA, self).__init__()
        self.S = nn.Parameter(torch.Tensor(1, num_seeds, dim_out))
        nn.init.xavier_uniform_(self.S)
        self.mab = MAB(dim_out, dim_in, dim_out, num_heads, ln=ln,  numlayers=numlayers)

    def forward(self, X):
        return self.mab(self.S.repeat(X.size(0), 1, 1), X)

# ============================ Transformer Layer =================================
class TransformerLayer(nn.Module):
    def __init__(self, 
                 input_vdim, 
                 input_edim, 
                 output_vdim, 
                 output_edim,
                 weight_dim,
                 pos_dim = 0,
                 att_type_v = "RankAdd",
                 agg_type_v = "PrevQ",
                 att_type_e = "RankAdd",
                 agg_type_e = "PrevQ",
                 num_att_layer = 2,
                 dim_hidden = 128,
                 num_heads=4, 
                 num_inds=4,
                 dropout=0.6,
                 ln=False,
                 activation=F.relu):
        super(TransformerLayer, self).__init__()
        
        self.num_heads = num_heads
        self.num_inds = num_inds
        self.input_vdim = input_vdim
        self.input_edim = input_edim
        self.hidden_dim = dim_hidden
        self.output_vdim = output_vdim
        self.output_edim = output_edim
        self.weight_dim = weight_dim
        self.pos_dim = pos_dim
        self.att_type_v = att_type_v
        self.agg_type_v = agg_type_v
        self.att_type_e = att_type_e
        self.agg_type_e = agg_type_e
        self.num_att_layer = num_att_layer
        self.activation = activation
        self.dropout = dropout
        self.lnflag = ln
        
        if self.att_type_v == "RankAdd":
            self.pe_v = nn.Linear(weight_dim, input_vdim)
        if self.att_type_e == "RankAdd":
            self.pe_e = nn.Linear(weight_dim, output_edim)
        self.dropout = nn.Dropout(dropout)
            
        # For Node -> Hyperedge
        #     encoding part: create new node representation specialized in hyperedge
        dimension = input_vdim
        self.enc_v = nn.ModuleList()
        for _ in range(self.num_att_layer):
            if self.att_type_v == "RankQ":
                self.enc_v.append(IMAB(weight_dim, dimension, dim_hidden, num_heads, num_inds, ln=ln))
                self.enc_v.append(ISAB(dim_hidden, dim_hidden, num_heads, num_inds, ln=ln))
                dimension = dim_hidden
            elif self.att_type_v in ["ITRE", "ShawRE", "RafRE"]:
                self.enc_v.append(ISAB(dimension, dim_hidden, num_heads, num_inds, ln=ln, RE=self.att_type_v, pos_dim=self.pos_dim))
                dimension = dim_hidden
            elif self.att_type_v != "NoAtt":
                self.enc_v.append(ISAB(dimension, dim_hidden, num_heads, num_inds, ln=ln))
                dimension = dim_hidden
        #     decoding part: aggregate embeddings
        self.dec_v = nn.ModuleList()
        if self.agg_type_v == "PrevQ":
            self.dec_v.append(MAB(input_edim, dimension, dim_hidden, num_heads, ln=ln))
        elif self.agg_type_v == "pure":
            self.dec_v.append(PMA(dimension,  dim_hidden, num_heads, 1, ln=ln, numlayers=1))
        elif self.agg_type_v == "pure2":
            self.dec_v.append(PMA(dimension,  dim_hidden, num_heads, 1, ln=ln, numlayers=2))
        # else: "AvgAgg"
        self.dec_v.append(nn.Dropout(dropout))
        self.dec_v.append(nn.Linear(dim_hidden, output_edim))
        
        # For Hyperedge -> Node
        dimension = output_edim
        self.enc_e = nn.ModuleList()
        for _ in range(self.num_att_layer):
            if self.att_type_e == "RankQ":
                self.enc_e.append(IMAB(weight_dim, dimension, dim_hidden, num_heads, num_inds, ln=ln))
                self.enc_e.append(ISAB(dim_hidden, dim_hidden, num_heads, num_inds, ln=ln))
                dimension = dim_hidden
            elif self.att_type_e != "NoAtt":
                self.enc_e.append(ISAB(dimension, dim_hidden, num_heads, num_inds, ln=ln))   
                dimension = dim_hidden
        #     decoding part: aggregate embeddings
        self.dec_e = nn.ModuleList()
        if self.agg_type_e == "PrevQ":
            self.dec_e.append(MAB(input_vdim, dimension, dim_hidden, num_heads, ln=ln))
        elif self.agg_type_e == "pure":
            self.dec_e.append(PMA(dimension, dim_hidden, num_heads, 1, ln=ln, numlayers=1))
        elif self.agg_type_e == "pure2":
            self.dec_e.append(PMA(dimension, dim_hidden, num_heads, 1, ln=ln, numlayers=2))
        self.dec_e.append(nn.Dropout(dropout))
        self.dec_e.append(nn.Linear(dim_hidden, output_vdim))
        
    def v_message_func(self, edges):
        if self.weight_dim > 0: # weight represents ranking information
            return {'q': edges.dst['feat'], 'v': edges.src['feat'], 'weight': edges.data['weight']}
        elif "RE" in self.att_type_v:
            return {'q': edges.dst['feat'], 'v': edges.src['feat'], 'p': edges.src['pos']}
        else:
            return {'q': edges.dst['feat'], 'v': edges.src['feat']}
        
    def e_message_func(self, edges):
        if self.weight_dim > 0: # weight represents ranking information
            return {'q': edges.dst['feat'], 'v': edges.src['feat'], 'weight': edges.data['weight']}
        else:
            return {'q': edges.dst['feat'], 'v': edges.src['feat']}

    def v_reduce_func(self, nodes):
        # nodes.mailbox['v' or 'q'].shape = (num batch, hyperedge size, feature dim)
        Q = nodes.mailbox['q'][:,0:1,:] # <- Because nodes.mailbox['q'][i,j] == nodes.mailbox['q'][i,j+1] 
        v = nodes.mailbox['v']
        if self.weight_dim > 0:
            P = None
            W = nodes.mailbox['weight']
        elif "RE" in self.att_type_v :
            P = nodes.mailbox['p']
            W = None
        else:
            P = None
            W = None
            
        # Encode
        if self.att_type_v == "RankAdd":
            v = v + self.pe_v(W)
        for i, layer in enumerate(self.enc_v):
            if i % 2 == 0 and self.att_type_v == "RankQ":
                v = layer(W, v)
            elif "RE" in self.att_type_v:
                v = layer(v, P)
            else:
                v = layer(v)
        v = self.dropout(v)
        # Decode
        o = v
        if self.agg_type_v == "AvgAgg":
            o = torch.mean(o, dim=1, keepdim=True)
        for i, layer in enumerate(self.dec_v):
            if i == 0 and self.agg_type_v == "PrevQ":
                o = layer(Q, o)
            else:
                o = layer(o)
        return {'o': o}
    
    def e_reduce_func(self, nodes):
        Q = nodes.mailbox['q'][:,0:1,:]
        v = nodes.mailbox['v']
        if self.weight_dim > 0:
            W = nodes.mailbox['weight']
        else:
            W = None

        # Encode
        if self.att_type_e == "RankAdd":
            v = v + self.pe_e(W)
        for i, layer in enumerate(self.enc_e):
            if i % 2 == 0 and self.att_type_e == "RankQ":
                v = layer(W, v)
            else:
                v = layer(v)
        v = self.dropout(v)
        
        # Decode
        o = v
        if self.agg_type_e == "AvgAgg":
            o = torch.mean(o, dim=1, keepdim=True)
        for i, layer in enumerate(self.dec_e):
            if i == 0 and self.agg_type_e == "PrevQ":
                o = layer(Q, o)
            else:
                o = layer(o)
                
        return {'o': o}
    
    def forward(self, g1, g2, vfeat, efeat, vpos=None):
        with g1.local_scope():
            g1.srcnodes['node'].data['feat'] = vfeat
            if vpos is not None:
                g1.srcnodes['node'].data['pos'] = vpos[:g1['in'].num_src_nodes()]
            g1.dstnodes['edge'].data['feat'] = efeat[:g1['in'].num_dst_nodes()]
            g1.update_all(self.v_message_func, self.v_reduce_func, etype='in')
            efeat = g1.dstnodes['edge'].data['o']
            efeat = efeat.squeeze(1)
        with g2.local_scope():       
            g2.srcnodes['edge'].data['feat'] = efeat
            g2.dstnodes['node'].data['feat'] = vfeat[:g2['con'].num_dst_nodes()]
            g2.update_all(self.e_message_func, self.e_reduce_func, etype='con')
            vfeat = g2.dstnodes['node'].data['o']
            vfeat = vfeat.squeeze(1)
        
        return [vfeat, efeat]
    
    
# ============================ Transformer ===============================
class Transformer(nn.Module): 
    def __init__(self, 
                 model,
                 input_vdim,
                 input_edim,
                 hidden_dim, 
                 vertex_dim,
                 edge_dim,
                 weight_dim=0,
                 pos_dim=0,
                 num_layers=2,
                 num_heads=4,
                 num_inds=4,
                 att_type_v = "RankAdd",
                 agg_type_v = "PrevQ",
                 att_type_e = "RankAdd",
                 agg_type_e = "PrevQ",
                 num_att_layer = 2,
                 layernorm = False,
                 dropout=0.6,
                 activation=F.relu):
        super(Transformer, self).__init__()
        self.num_layers = num_layers
        self.activation = activation
        
        self.layers = nn.ModuleList()               
        if num_layers == 1:
             self.layers.append(model(input_vdim, input_edim, vertex_dim, edge_dim, weight_dim=weight_dim, num_heads=num_heads, num_inds=num_inds, pos_dim=pos_dim,
                                      att_type_v=att_type_v, agg_type_v=agg_type_v, att_type_e = att_type_e, agg_type_e=agg_type_e, num_att_layer=num_att_layer,
                                      dropout=dropout, ln=layernorm, activation=None))
        else:
            for i in range(num_layers):
                if i == 0:
                    self.layers.append(model(input_vdim, input_edim, hidden_dim, hidden_dim, weight_dim=weight_dim, num_heads=num_heads, num_inds=num_inds, pos_dim=pos_dim,
                                             att_type_v=att_type_v, agg_type_v=agg_type_v, att_type_e = att_type_e, agg_type_e=agg_type_e, num_att_layer=num_att_layer,
                                             dropout=dropout, ln=layernorm, activation=self.activation))
                elif i == (num_layers - 1):
                    self.layers.append(model(hidden_dim, hidden_dim, vertex_dim, edge_dim, weight_dim=weight_dim, num_heads=num_heads, num_inds=num_inds, pos_dim=pos_dim,
                                             att_type_v=att_type_v, agg_type_v=agg_type_v, att_type_e = att_type_e, agg_type_e=agg_type_e, num_att_layer=num_att_layer,
                                             dropout=dropout, ln=layernorm, activation=None))
                else:
                    self.layers.append(model(hidden_dim, hidden_dim, hidden_dim, hidden_dim, weight_dim=weight_dim, num_heads=num_heads, num_inds=num_inds, pos_dim=pos_dim,
                                             att_type_v=att_type_v, agg_type_v=agg_type_v, att_type_e = att_type_e, agg_type_e=agg_type_e, num_att_layer=num_att_layer,
                                             dropout=dropout, ln=layernorm, activation=self.activation))
    
    def forward(self, blocks, vfeat, efeat, vpos=None):
        for l in range(self.num_layers):
            vfeat, efeat = self.layers[l](blocks[2*l], blocks[2*l+1], vfeat, efeat, vpos)
            
        return vfeat, efeat
    
    
    
    