1. Run 01-queue.py to generate the queue file (queue.json)
2. To run it locally, exectue 02-execute-queue-local.py
3. To run it on the cluster: 
    - Make sure to have IAMS installed on the cluster
    - Change username in 03-execute-queue-cluster.py to your username
    - Execute 03-execute-queue-cluster.py. You will be prompted for password and 2FA (once)
    - Wait until run is finished (you should get an email for start as well as finish/crash)
4. To run it on AWS:
    - Run 04a-execute-queue-AWS.py to upload the queue file and to schedule the job.
    - Once it-s finished, run 04b-download-results-AWS.py to download the results in a local folder
