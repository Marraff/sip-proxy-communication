#zdroj: https://github.com/tirfil/PySipFullProxy/blob/master/sipfullproxy.py
import sipfullproxy
import socketserver
import socket
import time
import sys
from sipfullproxy import *

HOST, PORT ='0.0.0.0', 5060

if __name__ == "__main__": 
    

    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',filename='proxy.log',level=logging.INFO,datefmt='%H:%M:%S')
    sipfullproxy.logging.info(time.strftime(" SIP bol spusteny na - %a, %d %b %Y %H:%M:%S ", time.localtime()))

    hostname = socket.gethostname()
    sipfullproxy.logging.info(hostname)
    ipaddress = socket.gethostbyname(hostname)
    if ipaddress == "127.0.0.1":
        ipaddress = sys.argv[1]
    sipfullproxy.logging.info(ipaddress)

    sipfullproxy.recordroute = "Record-Route: <sip:%s:%d;lr>" % (ipaddress,PORT)
    sipfullproxy.topvia = "Via: SIP/2.0/UDP %s:%d" % (ipaddress,PORT)
    sipfullproxy.server = socketserver.UDPServer((HOST, PORT), UDPHandler)
    print("Proxy server started at %s:%s" % (ipaddress, PORT))
    sipfullproxy.server.serve_forever()
   
