#    Copyright 2014 Philippe THIRION
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import socketserver
import re
import string
import socket
#import threading
import sys
import time
import logging

HOST, PORT = '0.0.0.0', 5060
rx_register = re.compile("^REGISTER")
rx_invite = re.compile("^INVITE")
rx_ack = re.compile("^ACK")
rx_prack = re.compile("^PRACK")
rx_cancel = re.compile("^CANCEL")
rx_bye = re.compile("^BYE")
rx_options = re.compile("^OPTIONS")
rx_subscribe = re.compile("^SUBSCRIBE")
rx_publish = re.compile("^PUBLISH")
rx_notify = re.compile("^NOTIFY")
rx_info = re.compile("^INFO")
rx_message = re.compile("^MESSAGE")
rx_refer = re.compile("^REFER")
rx_update = re.compile("^UPDATE")
rx_from = re.compile("^From:")
rx_cfrom = re.compile("^f:")
rx_to = re.compile("^To:")
rx_cto = re.compile("^t:")
rx_tag = re.compile(";tag")
rx_contact = re.compile("^Contact:")
rx_ccontact = re.compile("^m:")
rx_uri = re.compile("sip:([^@]*)@([^;>$]*)")
rx_addr = re.compile("sip:([^ ;>$]*)")
#rx_addrport = re.compile("([^:]*):(.*)")
rx_code = re.compile("^SIP/2.0 ([^ ]*)")
#toto som opravil
#rx_invalid = re.compile("^192\.168")
#rx_invalid2 = re.compile("^10\.")
#rx_cseq = re.compile("^CSeq:")
#rx_callid = re.compile("Call-ID: (.*)$")
#rx_rr = re.compile("^Record-Route:")
rx_request_uri = re.compile("^([^ ]*) sip:([^ ]*) SIP/2.0")
rx_route = re.compile("^Route:")
rx_contentlength = re.compile("^Content-Length:")
rx_ccontentlength = re.compile("^l:")
rx_via = re.compile("^Via:")
rx_cvia = re.compile("^v:")
rx_branch = re.compile(";branch=([^;]*)")
rx_rport = re.compile(";rport$|;rport;")
rx_contact_expires = re.compile("expires=([^;$]*)")
rx_expires = re.compile("^Expires: (.*)$")

# global dictionnary
recordroute = ""
topvia = ""
registrar = {}

def hexdump( chars, sep, width ):
    while chars:
        line = chars[:width]
        chars = chars[width:]
        line = line.ljust( width, '\000' )
        logging.debug("%s%s%s" % ( sep.join( "%02x" % ord(c) for c in line ),sep, quotechars( line )))

def quotechars( chars ):
	return ''.join( ['.', c][c.isalnum()] for c in chars )

def showtime():
    logging.debug(time.strftime("(%H:%M:%S)", time.localtime()))

class UDPHandler(socketserver.BaseRequestHandler):   
    
    def debugRegister(self):
        logging.debug("*** REGISTRAR ***")
        logging.debug("*****************")
        for key in registrar.keys():
            logging.debug("%s -> %s" % (key,registrar[key][0]))
        logging.debug("*****************")
    
    def changeRequestUri(self):
        # change request uri
        md = rx_request_uri.search(self.data[0])
        if md:
            method = md.group(1)
            uri = md.group(2)
            #if registrar.has_key(uri):
            if uri in registrar:
                uri = "sip:%s" % registrar[uri][0]
            
                self.data[0] = "%s %s SIP/2.0" % (method,uri)
                
                print('uri: ',uri)
                print('method: ',method)

        
    def removeRouteHeader(self):
        # delete Route
        data = []
        for line in self.data:
            if not rx_route.search(line):
                data.append(line)
        return data
    
    def addTopVia(self):
        branch= ""
        data = []
        for line in self.data:
            if rx_via.search(line) or rx_cvia.search(line):
                md = rx_branch.search(line)
                if md:
                    branch=md.group(1)
                    via = "%s;branch=%sm" % (topvia, branch)
                    data.append(via)
                # rport processing
                if rx_rport.search(line):
                    text = "received=%s;rport=%d" % self.client_address
                    via = line.replace("rport",text)   
                else:
                    text = "received=%s" % self.client_address[0]
                    via = "%s;%s" % (line,text)
                data.append(via)
            else:
                data.append(line)
        return data
                
    def removeTopVia(self):
        data = []
        for line in self.data:
            if rx_via.search(line) or rx_cvia.search(line):
                if not line.startswith(topvia):
                    data.append(line)
            else:
                data.append(line)
        return data
        
    def checkValidity(self,uri):
        addrport, socket, client_addr, validity = registrar[uri]
        now = int(time.time())
        if validity > now:
            return True
        else:
            del registrar[uri]
            logging.warning("registration for %s has expired" % uri)
            return False
    
    def getSocketInfo(self,uri):
        addrport, socket, client_addr, validity = registrar[uri]
        return (socket,client_addr)
        
    def getDestination(self):
        destination = ""
        for line in self.data:
            if rx_to.search(line) or rx_cto.search(line):
                md = rx_uri.search(line)
                if md:
                    destination = "%s@%s" %(md.group(1),md.group(2))
                break
        return destination
                
    def getOrigin(self):
        origin = ""
        for line in self.data:
            if rx_from.search(line) or rx_cfrom.search(line):
                md = rx_uri.search(line)
                if md:
                    origin = "%s@%s" %(md.group(1),md.group(2))
                break
        return origin
        
    def sendResponse(self,code):
        request_uri = "SIP/2.0 " + code
        self.data[0]= request_uri
        index = 0
        data = []
        for line in self.data:
            data.append(line)
            if rx_to.search(line) or rx_cto.search(line):
                if not rx_tag.search(line):
                    data[index] = "%s%s" % (line,";tag=123456")
            if rx_via.search(line) or rx_cvia.search(line):
                # rport processing
                if rx_rport.search(line):
                    text = "received=%s;rport=%d" % self.client_address
                    data[index] = line.replace("rport",text) 
                else:
                    text = "received=%s" % self.client_address[0]
                    data[index] = "%s;%s" % (line,text)      
            if rx_contentlength.search(line):
                data[index]="Content-Length: 0"
            if rx_ccontentlength.search(line):
                data[index]="l: 0"
            index += 1
            if line == "":
                break
        data.append("")
        #text = string.join(data,"\r\n")
        text = "\r\n".join(data).encode()
        self.socket.sendto(text,self.client_address)
        showtime()
        ######
        if (data[0] == 'SIP/2.0 100 Trying'):
            data[0] = 'SIP/2.0 100 Skusam'
        if (data[0] == 'SIP/2.0 200 Ok'):
            data[0] = 'SIP/2.0 200 Vporiadku'
        if (data[0] == 'SIP/2.0 486 Busy Here'):
            data[0] = 'SIP/2.0 486 Obsadene'
        if (data[0] == 'SIP/2.0 202 Accepted'):
            data[0] = 'SIP/2.0 202 Akceptovane'
        if (data[0] == 'SIP/2.0 180 Ringing'):
            data[0] = 'SIP/2.0 180 Zvonim'
        if (data[0] == 'SIP/2.0 603 Decline'):
            data[0] = 'SIP/2.0 603 Zrusene'


        #print("<<< %s" % data[0])
        logging.info("<<< %s" % data[0])
        logging.debug("---\n<< server send [%d]:\n%s\n---" % (len(text),text))
        
    def processRegister(self):
        fromm = ""
        contact = ""
        contact_expires = ""
        header_expires = ""
        expires = 0
        validity = 0
        authorization = ""
        index = 0
        auth_index = 0
        data = []
        size = len(self.data)
        for line in self.data:
            if rx_to.search(line) or rx_cto.search(line):
                md = rx_uri.search(line)
                if md:
                    fromm = "%s@%s" % (md.group(1),md.group(2))
            if rx_contact.search(line) or rx_ccontact.search(line):
                md = rx_uri.search(line)
                if md:
                    contact = md.group(2)
                else:
                    md = rx_addr.search(line)
                    if md:
                        contact = md.group(1)
                md = rx_contact_expires.search(line)
                if md:
                    contact_expires = md.group(1)
            md = rx_expires.search(line)
            if md:
                header_expires = md.group(1)
        
        #if rx_invalid.search(contact) or rx_invalid2.search(contact):
        #   if registrar.has_key(fromm):
        #       del registrar[fromm]
        #   self.sendResponse("488 Not Acceptable Here")    
        #   return
        if len(contact_expires) > 0:
            expires = int(contact_expires)
        elif len(header_expires) > 0:
            expires = int(header_expires)
            
        if expires == 0:
            #if registrar.has_key(fromm):
            if fromm in registrar:
                del registrar[fromm]
                self.sendResponse("200 Vporiadku")
                return
        else:
            now = int(time.time())
            validity = now + expires
            
    
        logging.info("From: %s - Contact: %s" % (fromm,contact))
        logging.debug("Client address: %s:%s" % self.client_address)
        logging.debug("Expires= %d" % expires)
        registrar[fromm]=[contact,self.socket,self.client_address,validity]
        self.debugRegister()
        self.sendResponse("200 Vporiadku")
        
    def processInvite(self):
        logging.debug("-----------------")
        logging.debug(" INVITE received ")
        logging.debug("-----------------")
        origin = self.getOrigin()
        #if len(origin) == 0 or not registrar.has_key(origin):
        if len(origin) == 0 or not origin in registrar:
            self.sendResponse("400 Zlá požiadavka")
            return
        destination = self.getDestination()
        if len(destination) > 0:
            logging.info("destination %s" % destination)
            #if registrar.has_key(destination) and self.checkValidity(destination):
            if destination in registrar and self.checkValidity(destination):
                socket,claddr = self.getSocketInfo(destination)
                #self.changeRequestUri()
                self.data = self.addTopVia()
                data = self.removeRouteHeader()
                #insert Record-Route
                data.insert(1,recordroute)
                #text = string.join(data,"\r\n")
                text = "\r\n".join(data).encode()
                socket.sendto(text , claddr)
                showtime()
                ######
                if (data[0] == 'SIP/2.0 100 Trying'):
                    data[0] = 'SIP/2.0 100 Skusam'
                if (data[0] == 'SIP/2.0 200 Ok'):
                    data[0] = 'SIP/2.0 200 Vporiadku'
                if (data[0] == 'SIP/2.0 486 Busy Here'):
                    data[0] = 'SIP/2.0 486 Obsadene'
                if (data[0] == 'SIP/2.0 202 Accepted'):
                    data[0] = 'SIP/2.0 202 Akceptovane'
                if (data[0] == 'SIP/2.0 180 Ringing'):
                    data[0] = 'SIP/2.0 180 Zvonim'
                if (data[0] == 'SIP/2.0 603 Decline'):
                    data[0] = 'SIP/2.0 603 Zrusene'


                #print("<<< %s" % data[0])
                logging.info("<<< %s" % data[0])
                logging.debug("---\n<< server send [%d]:\n%s\n---" % (len(text),text))
            else:
                self.sendResponse("480 Dočasne nedostupné")
        else:
            self.sendResponse("500 Server vnútorný error")
                
    def processAck(self):
        logging.debug("--------------")
        logging.debug(" ACK received ")
        logging.debug("--------------")
        destination = self.getDestination()
        if len(destination) > 0:
            logging.info("destination %s" % destination)
            #if registrar.has_key(destination):
            if destination in registrar:
                socket,claddr = self.getSocketInfo(destination)
                #self.changeRequestUri()
                self.data = self.addTopVia()
                data = self.removeRouteHeader()
                #insert Record-Route
                data.insert(1,recordroute)
                #text = string.join(data,"\r\n")
                text = "\r\n".join(data).encode()
                socket.sendto(text,claddr)
                showtime()
                #####
                if (data[0] == 'SIP/2.0 100 Trying'):
                    data[0] = 'SIP/2.0 100 Skusam'
                if (data[0] == 'SIP/2.0 200 Ok'):
                    data[0] = 'SIP/2.0 200 Vporiadku'
                if (data[0] == 'SIP/2.0 486 Busy Here'):
                    data[0] = 'SIP/2.0 486 Obsadene'
                if (data[0] == 'SIP/2.0 202 Accepted'):
                    data[0] = 'SIP/2.0 202 Akceptovane'
                if (data[0] == 'SIP/2.0 180 Ringing'):
                    data[0] = 'SIP/2.0 180 Zvonim'
                if (data[0] == 'SIP/2.0 603 Decline'):
                    data[0] = 'SIP/2.0 603 Zrusene'

                #print("<<< %s" % data[0])
                logging.info("<<< %s" % data[0])
                logging.debug( "---\n<< server send [%d]:\n%s\n---" % (len(text),text))
                
    def processNonInvite(self):
        logging.debug("----------------------")
        logging.debug(" NonInvite received   ")
        logging.debug("----------------------")
        origin = self.getOrigin()
        #if len(origin) == 0 or not registrar.has_key(origin):
        if len(origin) == 0 or not origin in registrar:
            self.sendResponse("400 Zlá požiadavka")
            return
        destination = self.getDestination()
        if len(destination) > 0:
            logging.info("destination %s" % destination)
            #if registrar.has_key(destination) and self.checkValidity(destination):
            if destination in registrar and self.checkValidity(destination):
                socket,claddr = self.getSocketInfo(destination)
                #self.changeRequestUri()
                self.data = self.addTopVia()
                data = self.removeRouteHeader()
                #insert Record-Route
                data.insert(1,recordroute)
                #text = string.join(data,"\r\n")
                text = "\r\n".join(data).encode()
                socket.sendto(text , claddr)
                showtime()
                ####
                if (data[0] == 'SIP/2.0 100 Trying'):
                    data[0] = 'SIP/2.0 100 Skusam'
                if (data[0] == 'SIP/2.0 200 Ok'):
                    data[0] = 'SIP/2.0 200 Vporiadku'
                if (data[0] == 'SIP/2.0 486 Busy Here'):
                    data[0] = 'SIP/2.0 486 Obsadene'
                if (data[0] == 'SIP/2.0 202 Accepted'):
                    data[0] = 'SIP/2.0 202 Akceptovane'
                if (data[0] == 'SIP/2.0 180 Ringing'):
                    data[0] = 'SIP/2.0 180 Zvonim'
                if (data[0] == 'SIP/2.0 603 Decline'):
                    data[0] = 'SIP/2.0 603 Zrusene'


                #print("<<< %s" % data[0])
                logging.info("<<< %s" % data[0])
                logging.debug("---\n<< server send [%d]:\n%s\n---" % (len(text),text))    
            else:
                self.sendResponse("406 neakceptovateľné")
        else:
            self.sendResponse("500 Server vnútorný Error")
                
    def processCode(self):
        origin = self.getOrigin()
        if len(origin) > 0:
            logging.debug("origin %s" % origin)
            #if registrar.has_key(origin):
            if origin in registrar:
                socket,claddr = self.getSocketInfo(origin)
                self.data = self.removeRouteHeader()
                data = self.removeTopVia()
                #text = string.join(data,"\r\n")
                text = "\r\n".join(data).encode()
                socket.sendto(text,claddr)
                showtime()
                ####
                if (data[0] == 'SIP/2.0 100 Trying'):
                    data[0] = 'SIP/2.0 100 Skusam'
                if (data[0] == 'SIP/2.0 200 Ok'):
                    data[0] = 'SIP/2.0 200 Vporiadku'
                if (data[0] == 'SIP/2.0 486 Busy Here'):
                    data[0] = 'SIP/2.0 486 Obsadene'
                if (data[0] == 'SIP/2.0 202 Accepted'):
                    data[0] = 'SIP/2.0 202 Akceptovane'
                if (data[0] == 'SIP/2.0 180 Ringing'):
                    data[0] = 'SIP/2.0 180 Zvonim'
                if (data[0] == 'SIP/2.0 603 Decline'):
                    data[0] = 'SIP/2.0 603 Zrusene'

                #print("<<< %s" % data[0])
                logging.info("<<< %s" % data[0])
                logging.debug("---\n<< server send [%d]:\n%s\n---" % (len(text),text))
                
                
    def processRequest(self):
        #print "processRequest"
        if len(self.data) > 0:
            request_uri = self.data[0]
            if rx_register.search(request_uri):
                self.processRegister()
            elif rx_invite.search(request_uri):
                self.processInvite()
            elif rx_ack.search(request_uri):
                self.processAck()
            elif rx_bye.search(request_uri):
                self.processNonInvite()
            elif rx_cancel.search(request_uri):
                self.processNonInvite()
            elif rx_options.search(request_uri):
                self.processNonInvite()
            elif rx_info.search(request_uri):
                self.processNonInvite()
            elif rx_message.search(request_uri):
                self.processNonInvite()
            elif rx_refer.search(request_uri):
                self.processNonInvite()
            elif rx_prack.search(request_uri):
                self.processNonInvite()
            elif rx_update.search(request_uri):
                self.processNonInvite()
            elif rx_subscribe.search(request_uri):
                self.sendResponse("200 Vporiadku")
            elif rx_publish.search(request_uri):
                self.sendResponse("200 Vporiadku")
            elif rx_notify.search(request_uri):
                self.sendResponse("200 Vporiadku")
            elif rx_code.search(request_uri):
                self.processCode()
            else:
                logging.error("request_uri %s" % request_uri)          
                #print "message %s unknown" % self.data
    
    def handle(self):
        #socket.setdefaulttimeout(120)
        data = self.request[0].decode('windows-1252')
        #data = bytes(data,'utf-8')
        self.data = data.split("\r\n")
        self.socket = self.request[1]
        request_uri = self.data[0]
        if rx_request_uri.search(request_uri) or rx_code.search(request_uri):
            showtime()

            if (request_uri== 'SIP/2.0 100 Trying'):
                request_uri = 'SIP/2.0 100 Skusam'
            if (request_uri == 'SIP/2.0 200 Ok'):
                request_uri = 'SIP/2.0 200 Vporiadku'
            if (request_uri == 'SIP/2.0 486 Busy Here'):
                request_uri = 'SIP/2.0 486 Obsadene'
            if (request_uri == 'SIP/2.0 202 Accepted'):
               request_uri = 'SIP/2.0 202 Akceptovane'
            if (request_uri == 'SIP/2.0 180 Ringing'):
                request_uri = 'SIP/2.0 180 Zvonim'
            if (request_uri == 'SIP/2.0 603 Decline'):
                request_uri = 'SIP/2.0 603 Zrusene'

            logging.info(">>> %s" % request_uri)
            logging.debug("---\n>> server received [%d]:\n%s\n---" %  (len(data),data))
            logging.debug("Received from %s:%d" % self.client_address)
            self.processRequest()
        else:
            if len(data) > 4:
                showtime()
                logging.warning("---\n>> server received [%d]:" % len(data))
                hexdump(data,' ',16)
                logging.warning("---")

'''
if __name__ == "__main__":    
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',filename='proxy.log',level=logging.INFO,datefmt='%H:%M:%S')
    logging.info(time.strftime("%a, %d %b %Y %H:%M:%S ", time.localtime()))
    hostname = socket.gethostname()
    logging.info(hostname)
    ipaddress = socket.gethostbyname(hostname)
    if ipaddress == "127.0.0.1":
        ipaddress = sys.argv[1]
    logging.info(ipaddress)
    recordroute = "Record-Route: <sip:%s:%d;lr>" % (ipaddress,PORT)
    topvia = "Via: SIP/2.0/UDP %s:%d" % (ipaddress,PORT)
    server = socketserver.UDPServer((HOST, PORT), UDPHandler)
    server.serve_forever()
'''