from datetime import datetime

EPOCH = datetime(2023, 1, 1).timestamp() * 1000
previous_time = 0
seq = 0

mid = int(datetime.now().timestamp()) & 0xfff 

def create_snowflake():
    time = (datetime.now().timestamp() * 1000) - EPOCH
    if time == previous_time:
        seq += 1
    else:
        seq = 0

    return int(time) << 22 | mid << 11 | seq
