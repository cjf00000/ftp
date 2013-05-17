import socket, sys, re, os
import threading
import select

def panic(msg):
	print msg
	sys.exit(1)
  
def getFromCmd(tip, default):
	cmd = raw_input(tip)
	if cmd=="":
		cmd = default
	return cmd

def setUser(inst_socket, userName):
	inst_socket.send('USER %s\r\n' % userName)

def tryToLogin(inst_socket):
	msg = inst_socket.recv(1024)
	while msg[:3] != "230":
		if msg[:3] == "331":
			password = getFromCmd("Password:", "")
			inst_socket.send("PASS %s\r\n" % password)
		else:
			panic("tryToLogin: Unknown message %s" % msg)

		msg = inst_socket.recv(1024)

def doPWD(inst_socket):
	inst_socket.send("PWD\r\n")
	msg = inst_socket.recv(1024)
	match = re.match('257 "(/.*)" is current directory.', msg)
	if match is None:
		panic("PWD: can't parse %s" % msg)
	else:
		matches = match.group(1)
		print matches
		return matches

def doCD(inst_socket, argv):
	if (len(argv)!=2):
		panic("cd: syntax error")
		return
	
	target = argv[1]
	inst_socket.send("CWD %s\r\n" % target)

	assert_prefixby(inst_socket, "250")

def listen(ip, port):
	address = (ip, port)
	data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	data_socket.bind(address)
	data_socket.listen(5)

	return data_socket

def portToHex(port):
	return str(port/256) + ',' + str(port%256)

def assert_ok(inst_socket):
	assert_prefixby(inst_socket, "200")

def assert_prefixby(inst_socket, prefix):
	msg = inst_socket.recv(1024)
	if (msg[:len(prefix)] != prefix):
		panic("Assert prefixby failed: %s is not prefix by %s." % (msg, prefix))

def doPASV(inst_socket):
	inst_socket.send('PASV\r\n')
	cmd = inst_socket.recv(1024)

	match = re.match(".*\((.*)\).*", cmd)
	cmd = match.groups(1)

	ips = cmd[0].split(',')
	ip = ips[0] + '.' + ips[1] + '.' + ips[2] + '.' + ips[3]
	port = int(ips[4])*256 + int(ips[5])

	return (ip, port)

def doLIST(inst_socket):
	address = doPASV(inst_socket)

	data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	data_socket.connect( address )

	inst_socket.send("LIST\r\n")
	assert_prefixby(inst_socket, "150")
	
	msg = data_socket.recv(1024)
	
	assert_prefixby(inst_socket, "226")
	data_socket.close()

	return msg


def doGET(inst_socket, argv):
	address = doPASV(inst_socket)

	data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	data_socket.connect( address )

	inst_socket.send("RETR %s\r\n" % argv[1])
	assert_prefixby(inst_socket, "150")

	msg = data_socket.recv(1048576)
	fout = open(argv[1], "w")
	fout.write(msg)
	fout.close()

	assert_prefixby(inst_socket, "226")

	data_socket.close()

def doPUT(inst_socket, argv):
	address = doPASV(inst_socket)

	data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	data_socket.connect( address )

	inst_socket.send("STOR %s\r\n" % argv[1])
	assert_prefixby(inst_socket, "150")

	fin = open(argv[1], "r")
	msg = fin.read()
	fin.close()
	
	data_socket.send(msg)
	data_socket.close()

	assert_prefixby(inst_socket, "226")

def showHelp():
	print '''Usage:
	pwd		show current working directory
	cd		change working directory
	ls		show content of working directory
	put <filename>	put filename to working directory
	get <filename>	get filename from working directory'''

address = ('192.168.245.97', 13321)
inst_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
inst_socket.connect(address)  
	  
welcome_cnt = 0
while (welcome_cnt < 3):
	welcome = inst_socket.recv(4096)
	print welcome
	welcome_cnt += welcome.count('\n')

userName = getFromCmd("UserName: (<empty> for anonymous)", "anonymous")

setUser(inst_socket, userName)
tryToLogin(inst_socket)

currentRemoteDirectory = doPWD(inst_socket)
currentLocalDirectory = os.getcwd()

while 1:
	cmd = getFromCmd("%s,%s> " % (currentLocalDirectory, currentRemoteDirectory), "")
	argv = cmd.split(' ')
	op = argv[0]

	if op=="pwd":
		currentRemoteDirectory = doPWD(inst_socket)
		print currentRemoteDirectory
	elif op=="ls":
		print doLIST(inst_socket)
	elif op == "cd": 
		doCD(inst_socket, argv)
		currentRemoteDirectory = doPWD(inst_socket)
	elif op == "get":
		doGET(inst_socket, argv)
	elif op == "put":
		doPUT(inst_socket, argv)
	elif op == "?":
		showHelp()
	elif op == "quit":
		break
	else:
		print 'Unsupported instruction %s' % cmd
		showHelp()

inst_socket.close()
