# Tutorial for creating a data streaming pipeline
A quick rundown on how to combine Flask, Kafka, Spark, Hadoop, Docker, and Presto to generate and analyze a live a data stream.

## Instrument API server to log events to Kafka
```python
#!/usr/bin/env python
import json
from kafka import KafkaProducer
from flask import Flask, request

app = Flask(__name__)
producer = KafkaProducer(bootstrap_servers='kafka:29092')


def log_to_kafka(topic, events):
    events.update(request.headers)
    producer.send(topic, json.dumps(events).encode())


@app.route("/")
def default_response():
    default_event = {'event_type': 'default'}
    log_to_kafka('events', default_event)
    return "This is the default response!\n"

@app.route("/purchase_a_sword")
def purchase_a_sword():
    purchase_sword_event = {'event_type': 'purchase_a_sword'}
    log_to_kafka('events', purchase_sword_event)
    return "Sword Purchased!\n"

@app.route("/join_a_guild")
def join_a_guild():
    join_guild_event = {'event_type': 'join_a_guild'}
    log_to_kafka('events', join_guild_event)
    return "Guild Joined!\n"
```

## Use Spark streaming to filter select event types from Kafka, land them into HDFS/parquet to make them available for analysis
Spin up cluster
```bash
docker-compose up -d
```


Create a topic
```bash
docker-compose exec kafka kafka-topics --create --topic events --partitions 1 --replication-factor 1 --if-not-exists --zookeeper zookeeper:32181
```


Run flask (host 0.0.0.0 allows us to recieve requests from anyone)
```bash
docker-compose exec mids env FLASK_APP=/w205/project-3-jennamorabito/game_api.py flask run --host 0.0.0.0
```


In a second terminal window, set up to watch Kafka
```bash
docker-compose exec mids kafkacat -C -b kafka:29092 -t events -o beginning
```
running kafkacat without -e so it will run continuously

 
In a third terminal window, stream
```bash
docker-compose exec spark spark-submit /w205/project-3-jennamorabito/stream_and_hive.py
```

## Use Apache Bench to generate test data for the pipeline
A script to generate events until inturrupted
```bash
#!/bin/bash

while true; do 
  docker-compose exec mids ab -n 10 -H "Host: user1.comcast.com" http://localhost:5000/ 
  docker-compose exec mids ab -n 10 -H "Host: user1.comcast.com" http://localhost:5000/join_a_guild
  docker-compose exec mids ab -n 10 -H "Host: user1.comcast.com" http://localhost:5000/purchase_a_sword
  docker-compose exec mids ab -n 10 -H "Host: user2.att.com" http://localhost:5000/
  docker-compose exec mids ab -n 10 -H "Host: user2.att.com" http://localhost:5000/join_a_guild
  docker-compose exec mids ab -n 10 -H "Host: user2.att.com" http://localhost:5000/purchase_a_sword
  sleep 10 
done
```
In a fourth terminal window, call
```bash
sh data_gen.sh
```


In a fifth terminal window, check what it wrote to Hadoop
```bash
docker-compose exec cloudera hadoop fs -ls /tmp/sword_purchases
```


## Read it with Presto and query
```bash
docker-compose exec presto presto --server presto:8080 --catalog hive --schema default
```

How many times have users joined a guild or purchased a sword?
```
presto:default> select count(*) from join_guild;
 _col0 
-------
  2540 
(1 row)
```
```
presto:default> select count(*) from sword_purchases;
 _col0 
-------
  3740 
(1 row)
```

How many distinct users are there?
```
presto:default> select count(distinct Host) from sword_purchases;
 _col0 
-------
     2 
(1 row)
```

How many swords did each user purchase?
```
presto:default> select Host, count(*) as count from sword_purchases group by Host;
       Host        | count 
-------------------+-------
 user1.comcast.com |  1870 
 user2.att.com     |  1870 
(2 rows)
```