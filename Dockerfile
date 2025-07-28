FROM ubuntu:16.04
RUN apt-get update
RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:jblgf0/python
RUN apt-get update
RUN apt-get install -y ffmpeg python3.9 net-tools curl vim
COPY stream.sh /usr/bin/stream.sh
RUN chmod +x /usr/bin/stream.sh
COPY forward.py /usr/bin/forward.py
RUN chmod +x /usr/bin/forward.py
COPY ffserver.conf /etc/ffserver.conf
ENV RTSP_URL rtsp://freja.hiof.no:1935/rtplive/definst/hessdalen03.stream
ENV FFMPEG_INPUT_OPTS  ""
ENV FFMPEG_OUTPUT_OPTS  ""
ENV FFSERVER_LOG_LEVEL "error"
ENV FFMPEG_LOG_LEVEL  "warning"
# Set the environment variable to disable output buffering
ENV PYTHONUNBUFFERED=1
ENTRYPOINT /usr/bin/forward.py
