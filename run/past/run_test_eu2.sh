cd ..
cuda=0
seedlist=("100") # "0" 
# for seed in ${seedlist[@]}
# do
#     CUDA_VISIBLE_DEVICES=${cuda} python train_wdgl_w.py --dataset_name emailEu --output_dim 2 --k 0 --embedder transformer --encode_type RankQ --decode_type PrevQ --num_layers 2 --scorer sm --scorer_num_layers 1 --vrank_input degree_nodecentrality,eigenvec_nodecentrality,pagerank_nodecentrality,kcore_nodecentrality --optimizer adam --bs 128 --dropout 0.7 --gamma 0.99 --dim_hidden 64 --lr 0.001 --dim_edge 128 --dim_vertex 128 --epochs 100 --test_epoch 5 --sampling 40 --evaltype test --fix_seed --seed ${seed} --use_gpu
# done
CUDA_VISIBLE_DEVICES=${cuda} python train_wdgl_w.py --dataset_name emailEu --output_dim 2 --k 0 --embedder transformer --encode_type RankQ --decode_type PrevQ --num_layers 2 --scorer sm --scorer_num_layers 1 --vrank_input degree_nodecentrality,eigenvec_nodecentrality,pagerank_nodecentrality,kcore_nodecentrality --optimizer adam --bs 128 --dropout 0.7 --gamma 0.99 --dim_hidden 64 --lr 0.001 --dim_edge 128 --dim_vertex 128 --epochs 100 --test_epoch 5 --sampling 40 --evaltype test --fix_seed --seed 10 --use_gpu