#!/bin/sh
train_data=$1
test_data=$2
cd /bi/libsvm-3.18/tools/
python easy.py $input_file $test_data 
