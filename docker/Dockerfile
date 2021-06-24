FROM amazonlinux:latest
RUN yum -y install which unzip aws-cli python37 git opencv opencv-devel opencv-python libSM.x86_64
RUN git clone --recursive https://github.com/domischi/IAMS.git /src
RUN pip3 install -r /src/requirements.txt
RUN pip3 install -r /src/IAMS/simulators/SpringBox/requirements.txt
ADD run_worker.sh /tmp/run_worker.sh
ADD worker.py /tmp/worker.py

ENV PYTHONPATH "${PYTHONPATH}:/src"
WORKDIR /tmp
USER nobody
ENTRYPOINT ["/tmp/run_worker.sh"]
