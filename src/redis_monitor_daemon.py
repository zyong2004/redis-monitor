import os
import sys

if __name__ == "__main__":
    curpath=os.path.split( os.path.realpath( sys.argv[0] ) )[0]
    os.chdir(curpath)
    
    from redis_monitor import redis_monitor
    montor= redis_monitor()
    montor.curpath=curpath
    print 'curpath:'+montor.curpath
    montor.start_daemon()