import json
import os

curpath=''

def get_settings():
    """Parses the settings from redis-live.conf.
    """
    # TODO: Consider YAML. Human writable, machine readable.
    global curpath
    if(curpath==''):
        curpath=os.path.abspath('.')
    
    return json.load(open(curpath+ "/redis_live.conf"))

def get_redis_servers():
    config = get_settings()
    return config["RedisServers"]

def get_redis_alerturi():
    config = get_settings()
    return config["sms_alert"]

def get_redis_stats_server():
    config = get_settings()
    return config["RedisStatsServer"]

def get_data_store_type():
    config = get_settings()
    return config["DataStoreType"]

def get_master_slave_sms_type():
    config = get_settings()
    return config['master_slave_sms']

def save_settings(redisServers,smsType):
    config = get_settings()
    config["RedisServers"]= redisServers;
    config['master_slave_sms']=smsType;
    
    data = json.dumps(config)
    data = data.replace('}', '}\r\n')
    output = open(os.path.abspath('.') + "/redis_live.conf", "w")
    output.truncate()
    output.write(data)
    output.close()
