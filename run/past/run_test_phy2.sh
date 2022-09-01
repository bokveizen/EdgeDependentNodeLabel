cd ..
cuda=1
seedlist=("0" "10" "100")
for seed in ${seedlist[@]}
do
    CUDA_VISIBLE_DEVICES=${cuda} python evaluate.py --dataset_name StackOverflowPhysics --k 0 --embedder hcha --num_layers 2 --scorer sm --scorer_num_layers 1 --optimizer adam --bs -1 --dropout 0.7 --gamma 0.99 --dim_hidden 64 --lr 0.03 --dim_edge 128 --dim_vertex 128 --epochs 100 --test_epoch 5 --sampling -1 --evaltype test --fix_seed --seed ${seed} --use_gpu
    CUDA_VISIBLE_DEVICES=${cuda} python evaluate.py --dataset_name StackOverflowPhysics --k 0 --embedder transformer --encode_type RankQ --decode_type PrevQ --num_layers 2 --scorer sm --scorer_num_layers 1 --vrank_input degree_nodecentrality,eigenvec_nodecentrality,pagerank_nodecentrality,kcore_nodecentrality --optimizer adam --bs 128 --dropout 0.7 --gamma 0.99 --dim_hidden 64 --lr 0.001 --dim_edge 128 --dim_vertex 128 --epochs 100 --test_epoch 5 --sampling 40 --evaltype test --fix_seed --seed ${seed} --use_gpu
done