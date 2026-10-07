FROM python:3.12-slim 

WORKDIR /merfish-processing-pipeline

COPY . .
RUN ls 
RUN pip install .


ENTRYPOINT ["merfish-pipe"]