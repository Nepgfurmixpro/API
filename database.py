import os
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.cqlengine import connection

db = Cluster(["173.31.60.92"], auth_provider=PlainTextAuthProvider(os.getenv('SCYLLA_USERNAME'), os.getenv('SCYLLA_PASSWORD')), connect_timeout=20000).connect()
db.set_keyspace('rsaproject')
connection.set_session(db)