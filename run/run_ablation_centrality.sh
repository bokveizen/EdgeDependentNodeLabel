cuda=0
seedset=("0" "10" "100" "500" "10000")

cd ..
for seed in ${seedset[@]}
do
    # Node-Edge-Eigencentrality
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --vorder_input "nev_nodecentrality" --eorder_input "nev_hedgecentrality" --embedder whatsnet --att_type_v OrderPE --agg_type_v PrevQ --att_type_e OrderPE --agg_type_e PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 64 --lr 0.0001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 100 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed
    # Core-Periphery Score
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --vorder_input "cp_nodecentrality" --embedder whatsnet --att_type_v OrderPE --agg_type_v PrevQ --att_type_e OrderPE --agg_type_e PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 64 --lr 0.0001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 10 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed
    # Vector Eigencentrality
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --vorder_input "ve0_nodecentrality,ve1_nodecentrality,ve2_nodecentrality,ve3_nodecentrality,ve4_nodecentrality,ve5_nodecentrality,ve6_nodecentrality,ve7_nodecentrality,ve8_nodecentrality,ve9_nodecentrality,ve10_nodecentrality" --eorder_input "ve_hedgecentrality" --embedder whatsnet --att_type_v OrderPE --agg_type_v PrevQ --att_type_e OrderPE --agg_type_e PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 64 --lr 0.0001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 10 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed
    # Total
    CUDA_VISIBLE_DEVICES=${cuda} python train.py --dataset_name StackOverflowBiology --vorder_input "degree_nodecentrality,eigenvec_nodecentrality,kcore_nodecentrality,pagerank_nodecentrality,nev_nodecentrality,cp_nodecentrality,ve0_nodecentrality,ve1_nodecentrality,ve2_nodecentrality,ve3_nodecentrality,ve4_nodecentrality,ve5_nodecentrality,ve6_nodecentrality,ve7_nodecentrality,ve8_nodecentrality,ve9_nodecentrality,ve10_nodecentrality" --embedder whatsnet --att_type_v OrderPE --agg_type_v PrevQ --att_type_e OrderPE --agg_type_e PrevQ --num_att_layer 2 --num_layers 2 --scorer sm --scorer_num_layers 1 --bs 128 --lr 0.0001 --sampling 40 --dropout 0.7 --optimizer "adam" --k 0 --gamma 0.99 --dim_hidden 64 --dim_edge 128 --dim_vertex 128 --epochs 100 --test_epoch 5 --evaltype test --save_epochs 1 --seed ${seed} --fix_seed
done
