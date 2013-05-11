# -*- coding: utf-8 -*-
#! /usr/bin/env python

from api.util import settings
from dataprovider.dataprovider import RedisLiveDataProvider
from threading import Timer
import redis
import datetime
import threading
import traceback
import time
import json
from daemonized import daemonized
import httplib
import urllib

class InfoThread(threading.Thread):
    def __init__(self, server, port, password=None):
        threading.Thread.__init__(self)
        self.server = server
        self.port = port
        self.password = password
        self.id = self.server + ":" + str(self.port)
        self._stop = threading.Event()

    def stop(self):
        """Stops the thread.
        """
        self._stop.set()

    def stopped(self):
        """Returns True if the thread is stopped, False otherwise.
        """
        return self._stop.is_set()

    def run(self):
        """Does all the work.
        """
        monitor_tick=2  #log times every sec
        reserved_min = 1440*7 # data reserved time,1day=1440
        
        
        stats_provider = RedisLiveDataProvider.get_provider()
        redis_client = redis.StrictRedis(host=self.server, port=self.port, db=0,
                                        password=self.password)

        last_expired_keys=0
        last_evicted_keys=0
        last_keyspace_hits=0
        last_keyspace_misses=0
        last_total_commands_processed=0
        last_role_status=""
        last_role={}
        
        doitems=0
        # process the results from redis
        while not self.stopped():
            time.sleep(monitor_tick)
            doitems+=1
            try:
                redis_info={}
                current_time = datetime.datetime.now()
                redis_info = redis_client.info()
                
                # not save,for it let aof too large in redis
#                 try:
#                     redis_info = redis_client.info()
#                 except Exception, e:
#                     redis_info['role']='down'
#                     redis_info['uptime_in_seconds']=0
#                     redis_info['total_commands_processed']=0
#                     redis_info['used_memory_human']=''
#                     redis_info['connected_clients']=''
#                     
#                     stats_provider.save_info_command(self.id, current_time,
#                                                  redis_info)
#                     print "==============================\n"
#                     print datetime.datetime.now()
#                     print traceback.format_exc()
#                     print "==============================\n"
#                     continue
#                             
#                 info all
#                 stats_provider.save_info_command(self.id, current_time,
#                                                  redis_info)
               
                #try remove history
                if(doitems %30==0):
                    delta = datetime.timedelta(seconds=reserved_min*60)
                    start = current_time - delta
                    stats_provider.delete_history(self.id,start)
                
                  
                #memory
                used_memory = int(redis_info['used_memory'])

                # used_memory_peak not available in older versions of redis
                try:
                    peak_memory = int(redis_info['used_memory_peak'])
                except:
                    peak_memory = used_memory
                
#                 stats_provider.save_memory_info(self.id, current_time,
#                                                 used_memory, peak_memory)
#                
                #keys info
                databases=[]
                for key in sorted(redis_info.keys()):
                    if key.startswith("db"):
                        database = redis_info[key]
                        database['name']=key
                        databases.append(database)
 
                expires=0
                persists=0
                for database in databases:
                    expires+=database.get("expires")
                    persists+=database.get("keys")-database.get("expires")
                
               
                expired_keys=redis_info["expired_keys"]
                evicted_keys=redis_info["evicted_keys"]
                keyspace_hits=redis_info["keyspace_hits"]
                keyspace_misses=redis_info["keyspace_misses"]
                total_commands_processed=redis_info["total_commands_processed"]
                
                expired=0
                evicted=0
                if(last_expired_keys>0 or last_evicted_keys>0):
                    expired=expired_keys-last_expired_keys
                    if(expired>=0):
                        expired= (int)(expired/monitor_tick)
                        last_expired_keys=expired_keys
                    else:
                        expired=0
                        last_expired_keys=0
                        
                    evicted=evicted_keys-last_evicted_keys 
                    if(evicted>=0):
                        evicted= (int)(evicted/monitor_tick)
                        last_evicted_keys= evicted_keys
                    else:
                        evicted=0
                        last_evicted_keys=0
                else:
                    last_expired_keys=expired_keys
                    last_evicted_keys=evicted_keys
                
                hit_rate=0
                if(last_keyspace_hits>0 or last_keyspace_misses>0):
                    hits=keyspace_hits-last_keyspace_hits
                    miss=keyspace_misses - last_keyspace_misses
                    if(hits>=0 and miss>=0):
                        total=hits+miss
                        if(total>0):
                            hit_rate= (int)((hits*100)/(hits+miss))
                            last_keyspace_hits=keyspace_hits
                            last_keyspace_misses=keyspace_misses
                    else:
                        last_keyspace_hits=0
                        last_keyspace_misses =0
                else:
                    last_keyspace_hits=keyspace_hits
                    last_keyspace_misses=keyspace_misses
                    
                commands=0
                if(last_total_commands_processed>0):
                    commands=total_commands_processed-last_total_commands_processed 
                    if(commands>=0):
                        commands=(int)(commands/monitor_tick)
                        last_total_commands_processed=total_commands_processed
                    else:
                        last_total_commands_processed=0
                        commands=0
                else:
                    last_total_commands_processed=total_commands_processed
                    
                stats_provider.save_keys_Info(self.id, current_time, expires, persists,
                                            expired,evicted,hit_rate,commands,used_memory, peak_memory)
                
                #master status
                role=redis_info["role"]
                role_status={}
                
                if(role=="master"):
                    connected_slaves=(int)(redis_info["connected_slaves"])
                    slaves=""
                    for i in range(0,connected_slaves):
                        slaves+=redis_info["slave"+(str)(i)]
                        
                    role_status={"role":role,"slaves":slaves}
                else:
                    master_host=redis_info["master_host"]
                    master_port=(str)(redis_info["master_port"])
                    master_link_status=redis_info["master_link_status"]
                    master_sync_in_progress=redis_info["master_sync_in_progress"]
                    role_status={"role":role,                                            
                                           "master_host_port":master_host+":"+master_port,
                                           "master_link_status":master_link_status,
                                           "master_sync_in_progress":master_sync_in_progress }
                
                role_cur=json.dumps(role_status)
                if(role_cur!=last_role_status):
                    #monitor first start,not save
                    if(last_role_status!=""):
                        stats_provider.save_status_info(self.id, current_time, role_status)
                        self.sendslavesms(role_status,last_role)
                        
                    last_role_status=role_cur
                    last_role=role_status

            except Exception, e:
                last_expired_keys=0
                last_evicted_keys=0
                last_keyspace_hits=0
                last_keyspace_misses=0
                last_total_commands_processed=0
                
                tb = traceback.format_exc()
                
                print "==============================\n"
                print datetime.datetime.now()
                print tb
                print "==============================\n"

    def sendslavesms(self,current,last):
        try:
            self.sendsmsInner(current,last)
        except Exception,ex:
            print ex
            
    def sendsmsInner(self,current,last):
        sms_repl=0;
        sms_stats=0;
        try:
            sms=settings.get_master_slave_sms_type()
            sms=sms.split(',')
            sms_repl=(int)(sms[0])
            sms_stats=(int)(sms[1])
        except:
            pass
        if(sms_repl==1 and current['role']!=last['role']):
            self.sendsms(self.id+'from:'+last['role']+'changeto:'+current['role'])
        elif(sms_stats==1):
            self.sendsms(self.id+",status changed:"+json.dumps(last))
    
    def ServiceDown(self):
        pass
    def sendsms(self,content):
        url="192.168.110.207:9999"
        try:
            url=settings.get_redis_alerturi()
        finally:
            pass
        
        conn = httplib.HTTPConnection(url) 
        print content
        conn.request("POST", "/SendSms",body= urllib.urlencode({'text':content}))
        r1 = conn.getresponse() 
        
        print r1.status, r1.reason 

class redis_monitor(daemonized):
    def __init__(self):
        self.threads = []
        self.active = True

    def run_daemon(self):
        redis_servers = settings.get_redis_servers()

        for redis_server in redis_servers:
            
            info = InfoThread(redis_server["server"], redis_server["port"],
                              redis_server.get("password", None))
            self.threads.append(info)
            info.setDaemon(True)
            info.start()
        # In this particular case, running a single MONITOR client can reduce 
        # the throughput by more than 50%. Running more MONITOR clients will 
        # reduce throughput even more.
        try:
            doitems=0
            while self.active:
                time.sleep(1)
                doitems+=1
                stats_provider = RedisLiveDataProvider.get_provider()
                #try collection DB like:redis aofrewrite
                if(doitems %3600==0):
                    stats_provider.collection_database()
                
        except (KeyboardInterrupt, SystemExit):
            self.stop()

    def stop(self):
        """Stops the monitor and all associated threads.
        """
        print "shutting down..."
        
        for t in self.threads:
                t.stop()
        self.active = False

if __name__ == '__main__':
    monitor = redis_monitor()
    monitor.start()
