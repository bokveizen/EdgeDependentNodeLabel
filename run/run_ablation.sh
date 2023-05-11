cd ..
cuda=1
seedlist=("0" "10" "100" "500" "10000")
for seed in ${seedlist[@]}
do
    # Positional Encoding Schemes
    # GraphIT/DK 
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --embedder whatsnet --att_type_v ITRE --agg_type_v PrevQ --att_type_e pure --agg_type_e PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 128 --lr 0.001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 10 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed --pe DK --pe_ablation
    # GraphIT/PRWK
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --embedder whatsnet --att_type_v ITRE --agg_type_v PrevQ --att_type_e pure --agg_type_e PrevQ --num_att_layer 2 --num_layers 1 --scorer sm --scorer_num_layers 1 --bs 128 --lr 0.001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 10 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed --pe PRWK --pe_ablation
    # Shaw/DK
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --embedder whatsnet --att_type_v ShawRE --agg_type_v PrevQ --att_type_e pure --agg_type_e PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 128 --lr 0.001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 10 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed --pe DK --pe_ablation
    # Shaw/PRWK
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --embedder whatsnet --att_type_v ShawRE --agg_type_v PrevQ --att_type_e pure --agg_type_e PrevQ --num_att_layer 2 --num_layers 1 --scorer sm --scorer_num_layers 1 --bs 64 --lr 0.001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 10 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed --pe PRWK --pe_ablation
    # WHATsNET w/ WholeOrderPE
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --vorder_input "degree_nodecentrality,eigenvec_nodecentrality,pagerank_nodecentrality,kcore_nodecentrality" --embedder whatsnet --att_type_v OrderPE --agg_type_v PrevQ --att_type_e pure --agg_type_e PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 128 --lr 0.001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 10 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed --whole_order
    # WHATsNET w/o Inducing Points
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --vorder_input "degree_nodecentrality,eigenvec_nodecentrality,pagerank_nodecentrality,kcore_nodecentrality" --embedder whatsnet --att_type_v OrderPE --agg_type_v PrevQ --att_type_e pure --agg_type_e PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 128 --lr 0.001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 10 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed --pe_ablation
    # LSPE
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --embedder whatsnetLSPE --att_type_v OrderPE --agg_type_v PrevQ --att_type_e OrderPE --agg_type_e PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 128 --lr 0.001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 100 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed
    # Replacing WithinATT in updating node embeddings
    # WHATsNET + HNHN
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --vorder_input "degree_nodecentrality,eigenvec_nodecentrality,pagerank_nodecentrality,kcore_nodecentrality" --embedder whatsnetHNHN --att_type_v OrderPE --agg_type_v PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 64 --lr 0.001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 10 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed
    # WHATsNET + HAT
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --vorder_input "degree_nodecentrality,eigenvec_nodecentrality,pagerank_nodecentrality,kcore_nodecentrality" --embedder whatsnetHAT --att_type_v OrderPE --agg_type_v PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 128 --lr 0.001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 10 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed
    # Numer of Inducing Points
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --vorder_input "degree_nodecentrality,eigenvec_nodecentrality,pagerank_nodecentrality,kcore_nodecentrality" --embedder whatsnet --att_type_v OrderPE --agg_type_v PrevQ --att_type_e OrderPE --agg_type_e PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 128 --lr 0.0001 --num_inds 2 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 10 --test_epoch 5 --num_inds 2 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --vorder_input "degree_nodecentrality,eigenvec_nodecentrality,pagerank_nodecentrality,kcore_nodecentrality" --embedder transformer --att_type_v OrderPE --agg_type_v PrevQ --att_type_e OrderPE --agg_type_e PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 64 --lr 0.0001 --num_inds 8 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 10 --test_epoch 5 --num_inds 8 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed
done
