#!/bin/sh

#BASEDIR="s3://dominikschildknecht/ma/data/run$RUN_INDEX"
#BASEDIR="s3://dominikschildknecht/ma/data"
#MYDIR="$BASEDIR/$((AWS_BATCH_JOB_ARRAY_INDEX+1))/"

echo "*********************************************"
echo "Path:" $PATH
echo "Python path:" $PYTHONPATH
echo "Current path: " $(pwd)
echo "S3 Basedir: " $BASEDIR
echo "This runners dir: " $MYDIR
echo "*********************************************"
echo "*********************************************"
echo "ENV:"
env
echo "*********************************************"
#echo "*********************************************"
#echo "Try getting the files:"
#S3GET="aws s3 cp --recursive $MYDIR /tmp/"
#echo $S3GET
#$S3GET
#echo "*********************************************"
echo "*********************************************"
cd /tmp/
echo "Try running the python script:"
RUN_CMD="python3 worker.py"
echo $RUN_CMD
$RUN_CMD
#echo "*********************************************"
#echo "*********************************************"
#echo "Reuploading the results"
#S3PUT="aws s3 cp --recursive /tmp/data/1/ $MYDIR"
#echo $S3PUT
#$S3PUT
#echo "*********************************************"
