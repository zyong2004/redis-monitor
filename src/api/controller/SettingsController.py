from BaseController import BaseController
from api.util import settings

class SettingsController(BaseController):

    def get(self):
        server_list=""
        for server in settings.get_redis_servers():
            server_list+= "%(server)s:%(port)s\r\n" % server
        
        sms_repl=0;
        sms_stats=0;
        try:
            sms=settings.get_master_slave_sms_type()
            sms=sms.split(',')
            sms_repl=(int)(sms[0])
            sms_stats=(int)(sms[1])
        except:
            pass
            
        servers = {"servers": server_list,"sms1":sms_repl,"sms2":sms_stats}
        self.write(servers)
    
    def post(self):
        try:
            server_list=self.get_argument("servers")
            sms1=(int)(self.get_argument("sms1"))
            sms2=(int)(self.get_argument("sms2"))
            sms= "%s,%s" %(sms1,sms2)
            
            servers=[]
            for server in server_list.split('\n'):
                eps=server.split(':')
                if(len(eps)!=2):
                    raise Exception('server Ip format error.');
                ip=eps[0]
                port=eps[1]
                
                servers.append({'server':ip,'port':(int)(port)})
            settings.save_settings(servers, sms)
            self.write({"status":200})
        except Exception,ex:
            self.write({"status":500,"error":ex.message})
        