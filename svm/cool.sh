#!/bin/sh
test_data=$1

echo $test_data > "data/test.csv"
echo $test_data >> "data/test.all.csv"

./svm-scale -r "result/demo.csv.range" "data/test.csv" > "data/test.csv.scale"
cat data/test.csv.scale >> data/test.csv.all.scale

./svm-predict -q "data/test.csv.scale" "result/demo.csv.model" "result/test.csv.predict"
cat result/test.csv.predict >> result/test.csv.all.predict

cat result/test.csv.predict
