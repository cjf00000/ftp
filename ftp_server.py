import socket, sys, re, os
import threading
import select
import time
import random

def panic(msg):
	print msg
	sys.exit(1)

def portToHex(port):
	return str(port/256) + ',' + str(port%256)

def addressToString(address):
	return address[0].replace('.', ',') + ',' + portToHex(address[1])

def dirMSG(path):
	msg = ""

	for fileName in os.listdir(path):
		msg = msg + fileName + '\r\n'

	return msg

inst_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
inst_listener.bind((socket.gethostname(), 13321))
inst_listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
inst_listener.listen(5)

base_directory = os.getcwd()
current_directory = "/"

while 1: 
	inst_socket, addr = inst_listener.accept()
	print 'Client', addr, ' connected'

	inst_socket.send("220-FileZilla Server version 0.9.41 beta\r\n")
	inst_socket.send("220-written by Tim Kosse (Tim.Kosse@gmx.de)\r\n")
	inst_socket.send("220 Please visit http://sourceforge.net/projects/filezilla/\r\n")

	while 1:
		msg = inst_socket.recv(1024)

		if (msg[:4] == "USER"):
			inst_socket.send("331 Password required for temp\r\n")

		elif (msg[:4] == "PASS"):
			inst_socket.send("230 Logged on\r\n")

		elif (msg[:3] == "PWD"):
			inst_socket.send('257 "%s" is current directory.\r\n' % current_directory)

		elif (msg[:3] == "CWD"):
			msg = msg[4:-2]
			print msg
			current_directory = current_directory + msg + "/"
			inst_socket.send('250 CWD successful. "%s" is current directory.\r\n'\
					% current_directory)

		elif (msg[:4] == "PASV"):
			data_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			data_listener.bind( (socket.gethostname(), random.randint(14000, 30000)) )
			data_listener.listen(5)
			
			inst_socket.send("227 Entering Passive Mode (%s)\r\n" \
					% addressToString(data_listener.getsockname()) )

		elif (msg[:4] == "LIST"):
			inst_socket.send("150 Connection accepted\r\n")
					
			data_socket, addr = data_listener.accept()
			msg = dirMSG(base_directory + current_directory)

			data_socket.send(msg)
			data_socket.close()
			data_listener.close()	
			
			inst_socket.send("226 Transfer OK")

		elif (msg[:4] == "RETR"):
			fileName = msg[5:-2]
			filePath = base_directory + current_directory + fileName

			inst_socket.send("150 Connection accepted\r\n")
					
			data_socket, addr = data_listener.accept()

			fin = open(filePath, "r")
			msg = fin.read()
			fin.close()

			data_socket.send(msg)
			data_socket.close()
			data_listener.close()	
			
			inst_socket.send("226 Transfer OK")

		elif (msg[:4] == "STOR"):
			fileName = msg[5:-2]
			filePath = base_directory + current_directory + fileName

			inst_socket.send("150 Connection accepted\r\n")
					
			data_socket, addr = data_listener.accept()

			content = data_socket.recv(1048576)

			fout = open(filePath, "w")
			fout.write(content)
			fout.close()

			data_socket.close()
			data_listener.close()	
			
			inst_socket.send("226 Transfer OK")

		else:
			panic("Unsupported instruction %s" % msg)


	inst_socket.close()

inst_listener.close()

