#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psutil
import os
import platform
import subprocess
import threading
import socket
import pickle
import struct
import time
import pprint as pp
from uuid import getnode as get_mac

import Network.Protocol as Protocol 
import Network.Package as Package 
import Common.ConfHandler as ConfHandler
 

"""
for key, value in collect_info().items():
	print("{} : {}".format(key,value))

saida = subprocess.run("free | grep Mem | tr -s ' ' | cut -d' ' -f2,3,4", shell=True, stdout=subprocess.PIPE)
print(saida)
mem_total, mem_used, *r = map(int,saida.stdout.strip().split(b" "))
print("Total: {0}\nLivre: {1}\nPorcentagem: {2:5.2f}%".format(mem_total,mem_used,mem_used/mem_total*100))

subprocess.run("gedit &", shell=True)
#capturando pid do processo
pid = subprocess.run("ps aux | grep gedit | tr -s ' ' | cut -d' ' -f2 | head -n1", shell=True, stdout=subprocess.PIPE).stdout
#matando processo com pid capturado
subprocess.run("kill -9 " + str(int(pid)), shell=True)
"""
# ao inves de imprimir na tela colocar em um arquivo de log

# achei a classe para manipular aquivo in-memory: io.BytesIO, bem útil do lado do servidor
def screenshot_mini():
	saida = subprocess.run("import -window root -resize 353x222 png:/dev/stdout", shell=True, stdout=subprocess.PIPE)
	return saida.stdout
	
	
def screenshot():
	saida = subprocess.run("import -window root -resize 1024x768 png:/dev/stdout", shell=True, stdout=subprocess.PIPE)
	return saida.stdout
	
def get_processes():#da pra fazer com -> for p in psutil.process_iter():
	#saida = subprocess.run("ps ux | tr -s ' ' | cut -d' ' -f2,8,11- | head -n -7", shell=True, stdout=subprocess.PIPE)
	saida = subprocess.run("ps ux | tr -s ' ' | cut -d' ' -f2,8,11- ", shell=True, stdout=subprocess.PIPE)
	saida = str(saida.stdout,encoding="utf-8")
	linhas = saida.splitlines()
	nlinhas = []
	for linha in linhas:
		nlinhas.append(linha.split(" ",maxsplit=2))
	return nlinhas[1:]
	
def collect_static_info(conf_data):	
	static_info = {}
	
	static_info["system"] = platform.system()
	static_info["release"] = platform.release()
	static_info["version"] = platform.version()
	static_info["machine"] = platform.machine()
	static_info["mac"] = ':'.join(("%012X" % get_mac())[i:i+2] for i in range(0, 12, 2))
	static_info["conf"] = conf_data
	# mac da placa de rede
	
	return static_info

def collect_dynamic_info():
	dynamic_info = {}
	#saida = subprocess.run("free | grep Mem | tr -s ' ' | cut -d' ' -f2,3,4", shell=True, stdout=subprocess.PIPE)
	#mem_total, mem_used, *r = map(int,saida.stdout.strip().split(b" "))
	#dynamic_info["mem"] = round((mem_used/mem_total),2)
	dynamic_info["mem"] = psutil.virtual_memory().percent/100
	dynamic_info["cpu"] = psutil.cpu_percent(0.1)/100
	dynamic_info["user"] = psutil.users()[0].name 
	#str(subprocess.run("whoami", shell=True, stdout=subprocess.PIPE).stdout.strip(),encoding="utf-8")
	return dynamic_info
	
def show_msg(notify_with, text):
	subprocess.run(notify_with + " '" + text + "'", shell=True)

def open_tray():
	subprocess.run("eject", shell=True)

def reboot():
	print("reboot")

def shutdown():
	print("shutdown")

def block_system():
	print("block system")

def install_pkg(lista_pkgs : str):
	print("installing ", lista_pkgs)

def uninstall_pkg(lista_pkgs : str):
	print("uninstalling ", lista_pkgs)

def update_system():
	print("update system")

def execute(comando, argumento=" ", answer=False): # retornar o sucesso da execucao do comando
	r = subprocess.run(comando + " " + argumento, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	success = not bool(r.returncode)
	print(r)
	return (success,(r.stdout + b"\n" + r.stderr).strip() if answer else None)
	
# sendinfo e discovery deve ficar na mesma thread, pq se o servidor cair no meio
# da sendinfo devera voltar para discovery (resolver)
# tirar o confhandler de dentro. deixar fora e passar uma copia dos dados.

_BUFFER		=	4096
class SendInfo(threading.Thread):
	
	def __init__(self, address, *, daemon, annouce_delay, host):
		super().__init__(daemon=daemon)
		self.address = address
		self.announce_delay = annouce_delay
		self.host = host
	
	
	def sendinfo(self):
		with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as cli:
			cli.settimeout(1.0)
			info = collect_dynamic_info()
			data = pickle.dumps(info,pickle.HIGHEST_PROTOCOL)
			pkg = Package.UDPPackageGenerator(Protocol.Info.INFO,self.host,_BUFFER,data)
			
			cli.sendto(next(pkg.packages()), self.address)				
			
			try:
				if cli.recv(1) == Protocol.Info.ACK:
					print("Transmissão Dynamic Info bem sucedida!")
			except socket.timeout:
				print("Erro transmissão Dynamic Info")
	
	def sendscreenshot(self):
		with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as cli:
			cli.settimeout(1.0)
			print("Sending Screenshot")
			data = screenshot_mini()
			
			pkgs = Package.UDPPackageGenerator(Protocol.Info.SCREEN,self.host,_BUFFER,data)
			for pkg in pkgs:
				cli.sendto(pkg, self.address)
				time.sleep(0.01)
			
			try:
				if cli.recv(1) == Protocol.Info.ACK:
					print("Transmissão Screenshot bem sucedida!")
			except socket.timeout:
				print("Erro transmissão Screenshot")
	
	
	def sendProcesses(self):
		with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as cli:
			cli.settimeout(1.0)
			print("Sending Processes")
			data = pickle.dumps(get_processes(),pickle.HIGHEST_PROTOCOL)
			
			pkgs = Package.UDPPackageGenerator(Protocol.Info.PROCESSES,self.host,_BUFFER,data)
			for pkg in pkgs:
				cli.sendto(pkg, self.address)
				time.sleep(0.01)
			
			try:
				if cli.recv(1) == Protocol.Info.ACK:
					print("Transmissão Processes bem sucedida!")
			except socket.timeout:
				print("Erro transmissão Processes")
	
	def run(self):
		while True:
			self.sendinfo()
			self.sendscreenshot()
			self.sendProcesses()
			time.sleep(self.announce_delay)



def main():
	conf = ConfHandler.ConfHandler(os.path.join(os.path.dirname(__file__),"client.conf"))
	
	host = (conf["lab"],conf["hostname"])
	
	delay = 0.2
	with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as cli:
		cli.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		
		# processo de descoberta
		while True:
			if conf["discovery"] == "on":
				print("Looking for CyberTeaServer")
				pkg = Package.UDPPackageGenerator(Protocol.Discovery.DISCOVERY,host,_BUFFER)
				cli.sendto(next(pkg.packages()), ("255.255.255.255", int(conf["server_port"])))
				##cli.sendto(Protocol.Discovery.DISCOVERY, ("255.255.255.255", int(conf["server_port"])))
				cli.settimeout(delay)
				
				try:
					data, address = cli.recvfrom(1)
					print("Server found at " + address[0])
				except socket.timeout:
					print("Server not found!")
					delay *= 2
					
					if delay > 10:
						print("There is no server on this network.")
						time.sleep(10)
					continue
			else:
				pass # concluir
			
			print("Sending Static Info")
			data = pickle.dumps(collect_static_info(conf.data),pickle.HIGHEST_PROTOCOL)
			pkg = Package.UDPPackageGenerator(Protocol.Discovery.STATIC_INFO,host,_BUFFER,data)
			
			cli.sendto(next(pkg.packages()), address)
			
			try:
				data = cli.recv(1)
				print("Discovery Process Complete")
			except socket.timeout:
				continue
			else:
				break
	
	si = SendInfo(address, daemon=True, annouce_delay=int(conf["annouce_delay"]),host=host)
	si.start()
	
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.connect(address)
		data = pickle.dumps(host,pickle.HIGHEST_PROTOCOL)
		sock.send(Protocol.Control.READY+data)
		print("READY TO BE CONTROLED")
		while True:
			
			todo = sock.recv(_BUFFER)
			
			if todo[:1] == Protocol.Control.SEND_MSG:
				notify_with = conf["notify_with"]
				show_msg(notify_with, str(todo[5:],encoding="utf-8"))
				
			elif todo[:1] == Protocol.Control.OPEN_TRAY:
				open_tray()
			
			elif todo[:1] == Protocol.Control.REBOOT:
				reboot()
				
			elif todo[:1] == Protocol.Control.SHUTDOWN:
				shutdown()
			
			elif todo[:1] == Protocol.Control.BLOCK_SYSTEM:
				block_system()
			
			elif todo[:1] == Protocol.Control.INSTALL_PKG:
				install_pkg(str(todo[5:],encoding="utf-8"))
			
			elif todo[:1] == Protocol.Control.UNINSTALL_PKG:
				uninstall_pkg(str(todo[5:],encoding="utf-8"))
			
			elif todo[:1] == Protocol.Control.UPDATE_SYSTEM:
				update_system()
			
			elif todo[:1] == Protocol.Control.BLOCK_PROGRAM:
				execute("kill -19",str(todo[5:],encoding="utf-8"))
			
			elif todo[:1] == Protocol.Control.UNBLOCK_PROGRAM:
				execute("kill -18",str(todo[5:],encoding="utf-8"))
				
			elif todo[:1] == Protocol.Control.KILL_PROGRAM:
				execute("kill -9",str(todo[5:],encoding="utf-8"))
			
			elif todo[:1] == Protocol.Control.SEND_CMD:
				saida = execute("",str(todo[5:],encoding="utf-8"),True)
				proto = Package.TCPPackage(Protocol.Control.ANSWER_CMD,saida[1])
				sock.send(proto.msg)
			
			elif todo[:1] == Protocol.Control.RECV_LIST_FILES:
				saida = execute("ls -l /home/$USER/Documentos | grep ^- | tr -s ' ' | cut -d' ' -f 9",answer=True)
				proto = Package.TCPPackage(Protocol.Control.SEND_LIST_FILES,saida[1])
				sock.send(proto.msg)
			
			elif todo[:1] == Protocol.Control.BYE:
				print("BYE...")
				break
	
    

main()
