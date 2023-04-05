import os
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.cqlengine import connection
import pika
from pika.exchange_type import ExchangeType
from dotenv import load_dotenv

load_dotenv()

db = Cluster(["173.31.60.92"], auth_provider=PlainTextAuthProvider(os.getenv('SCYLLA_USERNAME'), os.getenv('SCYLLA_PASSWORD')), connect_timeout=20000).connect()
db.set_keyspace('rsaproject')
connection.set_session(db)

conn = pika.BlockingConnection(pika.ConnectionParameters('173.31.60.92', credentials=pika.PlainCredentials(os.getenv('RABBITMQ_USERNAME'), os.getenv('RABBITMQ_PASSWORD'))))
pika_channel = conn.channel()

pika_channel.queue_declare(queue='events', durable=True)
pika_channel.exchange_declare(exchange='event', exchange_type=ExchangeType.fanout, durable=True)
pika_channel.queue_bind(exchange='event', queue='events')