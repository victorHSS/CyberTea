#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socketserver
import threading
import queue
import struct
import pickle
import time
from collections import defaultdict
from io import BytesIO

import Network.Protocol as Protocol
import Network.Package as Package


class IOSocketError(OSError):
	pass


_BUFFER	=	4096

class UDPRequestHandler(socketserver.BaseRequestHandler):
	
	# organizar com Call - ver car_registration_server.py
	
	def handle(self):
		data = self.request[0]
		socket = self.request[1]
		
		pkg = Package.UDPPackage(self.request[0])
		
		if pkg.type_msg == Protocol.Discovery.DISCOVERY:
			print("Servidor Descoberto")
			socket.sendto(Protocol.Discovery.REQUEST, self.client_address)
		
		elif pkg.type_msg == Protocol.Discovery.STATIC_INFO:
			print("Recebendo Static info")
			info = pickle.loads(pkg.data)
			socket.sendto(Protocol.Info.ACK, self.client_address)
			
			info["client_IP"] = self.client_address[0]
			UDPRequestHandler.work_queue_si.put((pkg.identity, info))
		
		elif pkg.type_msg == Protocol.Info.INFO:
			print("Recebendo Dynamic info")

			info = pickle.loads(pkg.data)
			socket.sendto(Protocol.Info.ACK, self.client_address)
			
			UDPRequestHandler.work_queue_di.put((pkg.identity,info))
		
		elif pkg.type_msg == Protocol.Info.SCREEN:
			if pkg.isHead:
				print("Recebendo Screenshot")
			
			with UDPRequestHandler.imgLock:
				UDPRequestHandler.img[pkg.identity].loads(pkg)
			 
				if UDPRequestHandler.img[pkg.identity].ready:
					socket.sendto(Protocol.Info.ACK, self.client_address)
					if not UDPRequestHandler.img[pkg.identity].lost:
						UDPRequestHandler.work_queue_img.put((pkg.identity,UDPRequestHandler.img[pkg.identity].info))
					print("Recepção Screenshot OK")
					#del UDPRequestHandler.img[pkg.identity]
					UDPRequestHandler.img[pkg.identity] = Protocol.UDPRePackager()
				
		elif pkg.type_msg == Protocol.Info.PROCESSES:
			
			if pkg.isHead:
				print("Recebendo Processos")
			with UDPRequestHandler.procsLock:
				UDPRequestHandler.procs[pkg.identity].loads(pkg)
			
				if UDPRequestHandler.procs[pkg.identity].ready:
					socket.sendto(Protocol.Info.ACK, self.client_address)
					info = pickle.loads(UDPRequestHandler.procs[pkg.identity].info)
					if not UDPRequestHandler.procs[pkg.identity].lost:
						UDPRequestHandler.work_queue_proc.put((pkg.identity,info))
					print("Recepção Processos OK")
					#del UDPRequestHandler.procs[pkg.identity]
					UDPRequestHandler.procs[pkg.identity]  = Package.UDPRePackager()
				
			

class DiscoveryService(socketserver.ThreadingMixIn, socketserver.UDPServer):
	pass


def startUDPServer(port : int):
	UDPRequestHandler.work_queue_si = queue.Queue()
	UDPRequestHandler.work_queue_di = queue.Queue()
	UDPRequestHandler.work_queue_img = queue.Queue()
	UDPRequestHandler.work_queue_proc = queue.Queue()
	UDPRequestHandler.img = defaultdict(Package.UDPRePackager)
	UDPRequestHandler.procs = defaultdict(Package.UDPRePackager)
	UDPRequestHandler.imgLock = threading.Lock()
	UDPRequestHandler.procsLock = threading.Lock()
	UDPserver = DiscoveryService(("0.0.0.0",port),UDPRequestHandler)
	UDPserverThread = threading.Thread(target=UDPserver.serve_forever)
	UDPserverThread.daemon = True
	UDPserverThread.start()
	
	return UDPserver, UDPRequestHandler.work_queue_si, UDPRequestHandler.work_queue_di, UDPRequestHandler.work_queue_img, UDPRequestHandler.work_queue_proc

class TCPRequestHandler(socketserver.BaseRequestHandler):
	
	# organizar com Call - ver car_registration_server.py
	
	def handle(self):
		data = self.request.recv(_BUFFER)
		
		if data[:1] == Protocol.Control.READY:
			key = pickle.loads(data[1:])
			#TCPRequestHandler.PCsAtivos[key]["control"]["socket"] = self.request
			queue_in = TCPRequestHandler.PCsAtivos[key]["control"]["queue_in"]
			queue_out = TCPRequestHandler.PCsAtivos[key]["control"]["queue_out"]
			print("RECV READY",key)
			# enviar para fila de saida que esta conectado?
			# Enviar SIM... CONECTADO
			
		while True:
			todo = queue_in.get()
			#print(todo)
			
			#tratar erro de pipe quebrado (try) caso o cliente se vá do nada...
			
			if todo[0] in  (Protocol.Control.SEND_MSG,
							Protocol.Control.INSTALL_PKG,
							Protocol.Control.UNINSTALL_PKG,
							Protocol.Control.BLOCK_PROGRAM,
							Protocol.Control.KILL_PROGRAM):
							
				proto = Package.TCPPackage(todo[0],bytes(todo[1],encoding="utf-8"))
				self.request.send(proto.msg)
			
			elif todo[0] == Protocol.Control.BYE:
				self.request.send(todo[0])
				break # exclusivo por causa do break
			
			elif todo[0] == Protocol.Control.SEND_CMD:
				proto = Package.TCPPackage(todo[0],bytes(todo[1],encoding="utf-8"))
				self.request.send(proto.msg)
				msg = self.request.recv(_BUFFER)
				queue_out.put((msg[:1], str(msg[5:],encoding="utf-8")))
			
			elif todo[0] == Protocol.Control.RECV_LIST_FILES:
				proto = Package.TCPPackage(todo[0])
				self.request.send(proto.msg)
				msg = self.request.recv(_BUFFER)
				files = str(msg[5:],encoding="utf-8").splitlines()
				queue_out.put((msg[:1], files ))
				
			else:
				self.request.send(todo[0])

			

class ControlService(socketserver.ThreadingMixIn, socketserver.TCPServer):
	pass

def startTCPServer(port : int, PCsAtivos : dict):
	TCPRequestHandler.PCsAtivos = PCsAtivos
	TCPserver = ControlService(("0.0.0.0",port),TCPRequestHandler)
	TCPserverThread = threading.Thread(target=TCPserver.serve_forever)
	TCPserverThread.daemon = True
	TCPserverThread.start()
	
	return TCPserver
	

	
	
	
	
	
	
	

