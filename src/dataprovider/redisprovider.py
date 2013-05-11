from api.util import settings
from datetime import datetime, timedelta
import redis
import json
import ast
import time


def datetime2_unix_str(timestamp):
    return (str)((int)(time.mktime(timestamp.timetuple())))

class RedisStatsProvider(object):
    """A Redis based persistance to store and fetch stats"""

    def __init__(self):
        # redis server to use to store stats
        stats_server = settings.get_redis_stats_server()
        self.server = stats_server["server"]
        self.port = stats_server["port"]
        self.conn = redis.StrictRedis(host=self.server, port=self.port, db=0)

#     def save_memory_info(self, server, timestamp, used, peak):
#       
#         data = {"timestamp": datetime2_unix_str(timestamp),
#                 "used": used,
#                 "peak": peak}
#         self.conn.zadd(server + ":memory", datetime2_unix_str(timestamp), data)

    def save_keys_Info(self, server,timestamp, expires, persists,expired,evicted
                     ,hit_rate,commands,used,peak):
        data = {"timestamp": datetime2_unix_str(timestamp),
                "expires": expires,
                "persists": persists,
                "expired":expired,
                "evicted":evicted,
                "hit_rate":hit_rate,
                "commands":commands,
                "used": used,
                "peak": peak}
        self.conn.zadd(server + ":keysinfo", datetime2_unix_str(timestamp), data)
    
    def save_status_info(self, server, timestamp, data):
        timestamp=datetime2_unix_str(timestamp)
        data['timestamp']=timestamp
        self.conn.zadd(server + ":status", timestamp, json.dumps(data))

    def save_info_command(self, server, timestamp, info):
        # info let aof file too large ... do not save       
        self.conn.set(server + ":Info", json.dumps(info))
    
    def delete_history(self,server,timestamp):
        begin=0
        end = int(datetime2_unix_str(timestamp))
        self.conn.zremrangebyscore(server + ":keysinfo", begin, end)
        # status for more then 3 month
        self.conn.zremrangebyscore(server + ":status", begin, end - (3600*24*90))
    
    def get_info(self, server):
        info = self.conn.get(server + ":Info")
        info = json.loads(info)
        return info

#     def get_memory_info(self, server, from_date, to_date):
#         memory_data = []
#         data=self.get_zset_data("memory", server, from_date, to_date)
#         for row in data:
#             memory_data.append([row[0],row[1]['peak'],row[1]['used']])
# 
#         return memory_data
    def collection_database(self):
        self.conn.bgrewriteaof()

    def get_status_info(self, server, from_date, to_date):
        return self.get_zset_data("status", server, from_date, to_date)
        
    def get_keys_info(self, server, from_date, to_date):
        rows=self.get_zset_data("keysinfo", server, from_date, to_date)
        keys=[]
        for row in rows:
            keys.append([row[0],row[1]["commands"],row[1]["expires"],row[1]["persists"],
                         row[1]["expired"],row[1]["evicted"],row[1]["hit_rate"],row[1]['peak'],row[1]['used']])
        return keys
        
    def get_zset_data(self,keyprefix, server, from_date, to_date):
        data = []
        start = int(datetime2_unix_str(from_date))
        end = int(datetime2_unix_str(to_date))
        rows = self.conn.zrangebyscore(server + ":"+keyprefix, start, end)

        count=len(rows)
        rate=1
        
        if(count> 400):
            rate=count/200
            
        index=0
        for row in rows:
            # TODO: Check to see if there's not a better way to do this. Using
            # eval feels like it could be wrong/dangerous... but that's just a
            # feeling.
            index+=1
            if(index%rate==0):
                row = ast.literal_eval(row)
              
                # convert the timestamp
                timestamp = datetime.fromtimestamp(int(row['timestamp']))
    
                data.append([tuple(timestamp.timetuple())[:-2], row])
        return data