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