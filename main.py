import sipfullproxy
import socketserver
import socket
import time
import sys

HOST, PORT = '0.0.0.0', 5060

if __name__ == "__main__":    
    sipfullproxy.logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',filename='proxy.log',level=sipfullproxy.logging.INFO,datefmt='%H:%M:%S')
    sipfullproxy.logging.info(time.strftime("%a, %d %b %Y %H:%M:%S ", time.localtime()))
    hostname = socket.gethostname()
    sipfullproxy.logging.info(hostname)
    ipaddress = socket.gethostbyname(hostname)
    if ipaddress == "127.0.0.1":
        ipaddress = sys.argv[1]
    sipfullproxy.logging.info(ipaddress)
    recordroute = "Record-Route: <sip:%s:%d;lr>" % (ipaddress,PORT)
    topvia = "Via: SIP/2.0/UDP %s:%d" % (ipaddress,PORT)
    server = socketserver.UDPServer((HOST, PORT), sipfullproxy.UDPHandler)
    server.serve_forever()