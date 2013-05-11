from BaseController import BaseController
from api.util import settings
import redis

class InfoListController(BaseController):

    def get(self):
        response = {}
        response['data']=[]
        for server in self.read_server_config():
            info=self.getStatsPerServer(server)
            
            info.update({
                "addr" : info.get("server_name")[0].replace(".", "_") +  str(info.get("server_name")[1]),
            })
    
            screen_strategy = 'normal'
            if info.get("status") == 'down':
                screen_strategy = 'hidden'
    
            info.update({
                "screen_strategy": screen_strategy,
            })

            #key = info.get("addr")
            response["data"].append(info)
                     

        self.write(response)
        
    def read_server_config(self):
        server_list = []
        redis_servers = settings.get_redis_servers()

        for server in redis_servers:
            server_list.append([server['server'],server['port']])

        return server_list