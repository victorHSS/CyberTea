#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

import os
import copy
import time
import queue
from collections import defaultdict

import pprint as pp


import Network.NetworkServer as Net
import Network.Protocol as Protocol
import Network.Package as Package
import Common.ConfHandler as ConfHandler


class MainHandler: 
	
	def __init__(self, builder):
		self.noteGeral = builder.get_object("notebookGeral")
		self.noteLabs = builder.get_object("noteLabs")
		self.gridPCs = builder.get_object("gridPCs")
		self.statusbar = builder.get_object("statusbar")
		
		self.sobre = builder.get_object("janelaSobre")
		self.preferencias = builder.get_object("janelaPreferencias")
		
		#parece que deixa lento...
		self.bPCs = [builder.get_object("bPC{0:0>2}".format(i)) for i in range(1,31)]
		self.imgPCs = {("Lab-{0:0>2}".format(1),"PC-{0:0>2}".format(i)):builder.get_object("imgL{0:0>2}PC{1:0>2}".format(1,i)) for i in range(1,31)}
		#pp.pprint(self.imgPCs)
		self.PCsAtivos = defaultdict(lambda : dict(active=False,static={},dynamic={},last_time_alive=None, 
								control=dict(socket=None,queue_in=queue.Queue(),queue_out=queue.Queue())))
		
		self.builder = builder
		
		conf = ConfHandler.ConfHandler(os.path.join(os.path.dirname(__file__),"server.conf"))
		
		self.UDPserver, self.work_queue_si, self.work_queue_di, self.work_queue_img, self.work_queue_proc = \
										Net.startUDPServer(int(conf["listen_port"]))
										
		self.TCPserver = Net.startTCPServer(int(conf["listen_port"]), self.PCsAtivos)
		
		#coletar periodicamente info de pcs
		GObject.timeout_add(1000,self.carregarInfoPCs)
		
		
	def hideWidget(self, widget, *args):
		widget.hide()
		return True
	
	def minimizarJanela(self, window):
		window.minimize()
	
	def ajustesIniciais(self, window):
		window.maximize()
		# pegar as configuracoes e habilitar/desabilitar hosts etc.
		conf = ConfHandler.ConfHandler(os.path.join(os.path.dirname(__file__),"server.conf"))
		self.ajustarBotoesPCSensiveis(int(conf["num_hosts"]))
		self.statusbar.push(self.statusbar.get_context_id("geral"),"Iniciado com sucesso!")
		
	
	def ajustarBotoesPCSensiveis(self, num_hosts : int):
		for button in self.bPCs[ 0 : num_hosts]:
			button.props.sensitive = True
			
		for button in self.bPCs[ num_hosts :]:
			button.props.sensitive = False
	
	#####
	#
	# Saida
	#
	
	
	def encerrar_todas_as_conexoes(self):
		for key, pc in self.PCsAtivos.items():
			try:
				pc["control"]["queue_in"].put((Protocol.Control.BYE,None))
				print("Bye {0} {1}".format(key[0],key[1]))
			except:
				continue
	
	def sair(self, *args):
		self.UDPserver.shutdown()
		self.UDPserver.server_close()
		
		self.encerrar_todas_as_conexoes()
		self.TCPserver.shutdown()
		self.TCPserver.server_close()
		
		Gtk.main_quit()

	def confirmarSaida(self, *args):
		janelaConfirmarSaida = self.builder.get_object("janelaConfirmarSaida")
		janelaConfirmarSaida.show_all()
		return True
		
		
	#
	# Saida
	#
	#####
	
	
	#####
	#
	# Info Tela Geral
	#
	
	def carregarInfoPCs(self):
		
		def _map(name_num):
			return int(name_num.split("-")[1])
		
		# funcao que coleta periodicamente as info estaticas dos pcs ativos + sistema
		print("Carregando info geral dos PCs")
		conf = ConfHandler.ConfHandler(os.path.join(os.path.dirname(__file__),"server.conf"),autoflush=False)
		
		#new_data = []
		while not self.work_queue_si.empty():
			key, data = self.work_queue_si.get_nowait() # pode retornar exceção empty caso precise esperar (a ver)
			self.PCsAtivos[key].update(dict(active=True,static=data,last_time_alive=time.time()))
			conf["mac_lab{0:0>2}_pc{1:0>2}".format(_map(key[0]),_map(key[1]))] = data["mac"]
			#new_data.append(data)
			self.work_queue_si.task_done()
		
		conf.flush()
		
		# atualizar img tela geral
		#for ndata in new_data:
		#	ipc = _map(ndata["conf"]["hostname"]) -1
		#	if ndata["system"].lower().startswith("linux"):
		#		self.imgPCs[ipc].set_from_file("imagens/pclinux.png")
		
		# pegar os dados mutaveis + atualizar alive
		while not self.work_queue_di.empty():
			key, data = self.work_queue_di.get_nowait()
			self.PCsAtivos[key]["active"]=True
			self.PCsAtivos[key]["dynamic"].update(data)
			self.PCsAtivos[key]["last_time_alive"] = time.time()
			if self.PCsAtivos[key]["static"]["system"].startswith("Linux"):
				self.imgPCs[key].set_from_file("imagens/pclinux.png")
			else:
				self.imgPCs[key].set_from_file("imagens/pcwindows.png")
			self.work_queue_di.task_done()
		
		#pegar screenshots
		while not self.work_queue_img.empty():
			key, img = self.work_queue_img.get_nowait()
			imgname = "/tmp/" + key[0]+key[1] + ".png"
			self.PCsAtivos[key]["dynamic"]["screenshot"] = imgname
			with open(imgname,"wb") as fimg:
				fimg.write(img)
			self.work_queue_img.task_done()
		
		#pegar processes
		while not self.work_queue_proc.empty():
			key, procs = self.work_queue_proc.get_nowait()
			self.PCsAtivos[key]["dynamic"]["processes"] = procs
			self.work_queue_proc.task_done()
		
		# procurar os inativos
		for key, value in self.PCsAtivos.items():
			#pp.pprint(key)
			#pp.pprint(self.PCsAtivos[key],compact=True)
			if value["last_time_alive"] and time.time() - value["last_time_alive"] > 10:
				self.PCsAtivos[key]["active"] = False
		
		
		return True
		
	
	#
	# Info Tela Geral
	#
	#####
		
	#####
	#
	# Detalhes PC
	#
	
	def updateDetalhes(self, key):
		imageStatus = self.builder.get_object("imageStatus")
		imageScreenshot = self.builder.get_object("imageScreenshot")
		imageSystem = self.builder.get_object("imageSystem")
		labelStatusPC = self.builder.get_object("labelStatusPC")
		labelStatusConectado = self.builder.get_object("labelStatusConectado")
		labelSistema = self.builder.get_object("labelSistema")
		labelUsuario = self.builder.get_object("labelUsuario")
		labelIP = self.builder.get_object("labelIP")
		labelMAC = self.builder.get_object("labelMAC")
		progressbarProcessamento = self.builder.get_object("progressbarProcessamento")
		progressbarMemoria = self.builder.get_object("progressbarMemoria")
		liststoreProcess = self.builder.get_object("liststoreProcess")
		buttonLigar = self.builder.get_object("buttonLigar")
		buttonConectar = self.builder.get_object("buttonConectar")
		buttonDesconectar = self.builder.get_object("buttonDesconectar")
		frameInteracoes = self.builder.get_object("frameInteracoes")
		
		buttonConectar.props.visible = False
		buttonDesconectar.props.visible = False
		
		if key in self.PCsAtivos and self.PCsAtivos[key]["active"]:
			buttonLigar.props.sensitive = False
			labelStatusPC.props.label = "Ligado" # if self.PCsAtivos[key]["active"] else "Desligado"
			imageStatus.set_from_file("imagens/" + 
							("statusLigadoConectado.png" if self.PCsAtivos[key]["active"] else "statusDesligado.png"))
			imageSystem.set_from_file("imagens/" + 
							("linuxlogo.png" if self.PCsAtivos[key]["static"]["system"].startswith("Linux") else "windowslogo.png"))
			labelStatusConectado.props.label = "Conectado" if self.PCsAtivos[key]["static"]["system"].startswith("Linux") else "Desconectado"
			labelSistema.props.label = self.PCsAtivos[key]["static"]["system"]
			labelUsuario.props.label = self.PCsAtivos[key]["dynamic"]["user"]
			labelIP.props.label = self.PCsAtivos[key]["static"]["client_IP"]
			labelMAC.props.label = self.PCsAtivos[key]["static"]["mac"]
			progressbarProcessamento.props.fraction = self.PCsAtivos[key]["dynamic"]["cpu"]
			progressbarMemoria.props.fraction = self.PCsAtivos[key]["dynamic"]["mem"]
			
			imgname = self.PCsAtivos[key]["dynamic"].get("screenshot",None)
			imageScreenshot.set_from_file(imgname if imgname else "sem_tela_sistema.png")
			
			if self.PCsAtivos[key]["static"]["system"].startswith("Linux"):
				self.imgPCs[key].set_from_file("imagens/pclinux.png")
			else:
				self.imgPCs[key].set_from_file("imagens/pcwindows.png")
				
			frameInteracoes.props.sensitive = True
			
			if not liststoreProcess.get_iter_first():
				self.atualizarProcesso()
			
		else:
			buttonLigar.props.sensitive = True
			labelStatusPC.props.label = "Desligado"
			imageStatus.set_from_file("imagens/statusDesligado.png")
			imageSystem.set_from_file("imagens/noSystem.png")
			labelStatusConectado.props.label = "Desconectado"
			labelSistema.props.label = ""
			labelUsuario.props.label = ""
			labelIP.props.label = ""
			labelMAC.props.label = ""
			progressbarProcessamento.props.fraction = 0.0
			progressbarMemoria.props.fraction = 0.0
			imageScreenshot.set_from_file("imagens/sem_tela_sistema.png")
			self.imgPCs[key].set_from_file("imagens/pcdesligado.png")
			liststoreProcess.clear()
			frameInteracoes.props.sensitive = False
	
	
	
	def carregarDetalhesPC(self):
		print("Carregando detalhes de {0} {1} ".format(*self.PC_em_visualizacao))
		key = self.PC_em_visualizacao
		self.updateDetalhes(key)
		
		
		if self.PC_em_visualizacao not in self.PCsAtivos: #falta considerar se está alive
			return True
		
		# processa a fila de chegada (control)
		queue = self.PCsAtivos[key]["control"]["queue_out"]
		while not queue.empty():
			todo = queue.get_nowait()
			if todo[0] == Protocol.Control.ANSWER_CMD:
				textviewSaidaComando = self.builder.get_object("textviewSaidaComando")
				textviewSaidaComando.props.buffer.props.text += todo[1] + "\n"
			
			elif todo[0] == Protocol.Control.SEND_LIST_FILES:
				lsArquivosCliente = self.builder.get_object("liststoreArquivosCliente")
				lsArquivosCliente.clear()
				for arq in todo[1]:
					lsArquivosCliente.append(("",arq))
				
		
		# envia solicitacoes pela fila de saída? (control)
		
		
		return True
		
	
	def botaoPCClicado(self, label):
		self.PC_em_visualizacao = ("Lab-{0:0>2}".format(self.noteLabs.props.page + 1),label.props.label)		
		key = self.PC_em_visualizacao
		self.idDetalhes = GObject.timeout_add(1000,self.carregarDetalhesPC)
		self.noteGeral.set_current_page(1)
		
		labelNomePC = self.builder.get_object("labelNomePC")
		labelNomePC.props.label = key[0] + " " + key[1]
		self.updateDetalhes(key)
		self.atualizarProcesso()
		
		
		# zerar as queues (control) (?)
		
		
	def botaoVoltarDetalhes(self, button):
		# remove o timeout do metodo carregarDetalhesPC
		GObject.source_remove(self.idDetalhes)
		# para a thread
		self.noteGeral.set_current_page(0)
		
	def escolhaSoftware(self, combo):
		comboboxSoftware = self.builder.get_object("comboboxSoftware")
		notebookSoftware = self.builder.get_object("notebookSoftware")
		
		notebookSoftware.props.page = comboboxSoftware.props.active 
	
	def escolhaArquivo(self, combo):
		comboboxArquivo = self.builder.get_object("comboboxArquivo")
		notebookArquivo = self.builder.get_object("notebookArquivo")
		
		notebookArquivo.props.page = comboboxArquivo.props.active
		
		key = self.PC_em_visualizacao
		
		if comboboxArquivo.props.active == 1: #receber arquivos
			self.PCsAtivos[key]["control"]["queue_in"].put_nowait((Protocol.Control.RECV_LIST_FILES,None))
		
		
	def botaoPreferenciasClienteClicado(self, button):
		janelaPreferenciasCliente = self.builder.get_object("janelaPreferenciasCliente")
		liststoreConfCliente = self.builder.get_object("liststoreConfCliente")
		
		if self.PC_em_visualizacao not in self.PCsAtivos:
			return
		
		liststoreConfCliente.clear()
		for item in self.PCsAtivos[self.PC_em_visualizacao]["static"]["conf"].items():
			liststoreConfCliente.append(item)
			
		janelaPreferenciasCliente.show_all()
	
	def atualizarProcesso(self, *args):
		liststoreProcess = self.builder.get_object("liststoreProcess")
		liststoreProcess.clear()
		key = self.PC_em_visualizacao
		
		if key not in self.PCsAtivos:
			return
		
		procs = self.PCsAtivos[key]["dynamic"].get("processes",None)
		if procs:
			for item in procs:
				status,color = {"S":("running","green"),"T":("blocked","yellow")}.get(item[1][0],("desc","blue"))
				liststoreProcess.append((item[0],item[2],status,color))
	
	#
	# Detalhes PC
	#
	#####
	
	#####
	#
	# Controles
	#
	
	def enviarMsg(self, button):
		textviewMsg = self.builder.get_object("textviewMsg")
		text = textviewMsg.props.buffer.props.text
		
		key = self.PC_em_visualizacao
		
		self.PCsAtivos[key]["control"]["queue_in"].put_nowait((Protocol.Control.SEND_MSG,text))
		
	def abrirBandeja(self, button):
		print("abrir bandeja")
		key = self.PC_em_visualizacao
		self.PCsAtivos[key]["control"]["queue_in"].put_nowait((Protocol.Control.OPEN_TRAY,None))
		
	def reiniciarPC(self, button):
		key = self.PC_em_visualizacao
		self.PCsAtivos[key]["control"]["queue_in"].put_nowait((Protocol.Control.REBOOT,None))
	
	def desligarPC(self, button):
		key = self.PC_em_visualizacao
		self.PCsAtivos[key]["control"]["queue_in"].put_nowait((Protocol.Control.SHUTDOWN,None))
	
	def bloquearPC(self, button):
		key = self.PC_em_visualizacao
		self.PCsAtivos[key]["control"]["queue_in"].put_nowait((Protocol.Control.BLOCK_SYSTEM,None))
	
	def instalarPacote(self, button):
		key = self.PC_em_visualizacao
		entryPacotesInstalar = self.builder.get_object("entryPacotesInstalar")
		lista_pkg = entryPacotesInstalar.props.text
		entryPacotesInstalar.props.text = ""
		self.PCsAtivos[key]["control"]["queue_in"].put_nowait((Protocol.Control.INSTALL_PKG,lista_pkg))
	
	def desinstalarPacote(self, button):
		key = self.PC_em_visualizacao
		entryDesinstalarPacote = self.builder.get_object("entryDesinstalarPacote")
		lista_pkg = entryDesinstalarPacote.props.text
		entryDesinstalarPacote.props.text = ""
		self.PCsAtivos[key]["control"]["queue_in"].put_nowait((Protocol.Control.UNINSTALL_PKG,lista_pkg))
	
	def atualizarSistema(self, button):
		key = self.PC_em_visualizacao
		self.PCsAtivos[key]["control"]["queue_in"].put_nowait((Protocol.Control.UPDATE_SYSTEM,None))
	
	def bloquearProcesso(self, button):
		key = self.PC_em_visualizacao
		treeviewselectionProcesso = self.builder.get_object("treeviewselectionProcesso")
		
		sel = treeviewselectionProcesso.get_selected()
		model = sel[0]
		row = sel[1]

		self.PCsAtivos[key]["control"]["queue_in"].put_nowait((Protocol.Control.BLOCK_PROGRAM,model[row][0]))
	
	def matarProcesso(self, button):
		key = self.PC_em_visualizacao
		treeviewselectionProcesso = self.builder.get_object("treeviewselectionProcesso")
		
		sel = treeviewselectionProcesso.get_selected()
		model = sel[0]
		row = sel[1]
		model[row][3] = "red"
		self.PCsAtivos[key]["control"]["queue_in"].put_nowait((Protocol.Control.KILL_PROGRAM,model[row][0]))
		
	#
	# Controles
	#
	#####
	
	#####
	#
	# Janela Screenshot
	#
	
	def abrirJanelaScreenshot(self, button):
		janelaScreenshot = self.builder.get_object("janelaScreenshot")
		janelaScreenshot.show_all()
		

	#
	# Janela Screenshot
	#
	#####
	
	#####
	#
	# Janela Shell
	#
	
	def abrirJanelaShell(self, button):
		janelaShell = self.builder.get_object("janelaShell")
		janelaShell.show_all()
		

	#
	# Janela Shell
	#
	#####
	
	#####
	#
	# Preferencias
	#
	
	def abrirPreferencias(self, menuitem):
		
		entryHostname = self.builder.get_object("entryHostname")
		entryPorta = self.builder.get_object("entryPorta")
		comboMaxHosts = self.builder.get_object("comboMaxHosts")		
		comboMaxLabs = self.builder.get_object("comboMaxLabs")		
		checkExcedentes = self.builder.get_object("checkExcedentes")
		checkAutoconectar = self.builder.get_object("checkAutoconectar")
		liststoreMAC = self.builder.get_object("liststoreMAC")
		
		try:
			with ConfHandler.ConfHandler(os.path.join(os.path.dirname(__file__),"server.conf")) as conf:
				entryHostname.props.text = conf["hostname"]
				entryPorta.props.text = conf["listen_port"]
				
				checkExcedentes.props.active =  True if conf["disable_excedent"] == "True" else False
				checkAutoconectar.props.active = True if conf["autoconnect"] == "True" else False
				
				
				comboMaxHosts.props.active = int(conf["num_hosts"]) -1
				comboMaxLabs.props.active = int(conf["num_labs"]) -1
				
				liststoreMAC.clear()
				for ilab in range(1,11):
					for ipc in range(1,31):
						key = "mac_lab{0:0>2}_pc{1:0>2}".format(ilab,ipc)
						if key in conf:
							liststoreMAC.append(("Lab-{0:0>2}".format(ilab),"PC-{0:0>2}".format(ipc),conf[key]))
						
		except (ConfError, KeyConfError):
			self.statusbar.push(self.statusbar.get_context_id("geral"),"Problemas ao carregar as preferências!")
		else:
			self.statusbar.push(self.statusbar.get_context_id("geral"),"Preferências carregadas com sucesso!")
			self.preferencias.show_all()
	
	def salvarPreferencias(self, button):
		
		entryHostname = self.builder.get_object("entryHostname")
		entryPorta = self.builder.get_object("entryPorta")
		comboMaxHosts = self.builder.get_object("comboMaxHosts")		
		comboMaxLabs = self.builder.get_object("comboMaxLabs")		
		checkExcedentes = self.builder.get_object("checkExcedentes")
		checkAutoconectar = self.builder.get_object("checkAutoconectar")
		
		try:
			with ConfHandler.ConfHandler("server.conf") as conf:
				
				conf["hostname"] = entryHostname.props.text 
				conf["listen_port"] = entryPorta.props.text
				
				conf["autoconnect"] = str(checkAutoconectar.props.active)
				conf["disable_excedent"] = str(checkExcedentes.props.active)
				
				conf["num_hosts"] = str(comboMaxHosts.props.active + 1)
				conf["num_labs"] = str(comboMaxLabs.props.active + 1)
		
				self.ajustarBotoesPCSensiveis(int(conf["num_hosts"]))
		except (ConfError, KeyConfError):
			self.statusbar.push(self.statusbar.get_context_id("geral"),"Problemas ao salvar as preferências!")
		else:
			self.statusbar.push(self.statusbar.get_context_id("geral"),"Preferências salvas com sucesso!")
		
		self.preferencias.hide()
	
	
	#
	# Preferencias
	#
	#####
	
	#####	
	#
	# Menu
	#
	
	
	def menuitemSobre(self, menuitem):
		self.sobre.show_all()
		
	#
	# Menu
	#
	#####
	
	#####
	#
	# Janela Sobre
	#
	
	def responseJanelaSobre(self, dialog, response):
		dialog.hide()
	
	#
	# Janela Sobre
	#
	#####
	
	#####
	#
	# Janela Shell
	#
	
	def executarComando(self, entry):
		textviewSaidaComando = self.builder.get_object("textviewSaidaComando")
		cmd = entry.props.text
		key = self.PC_em_visualizacao
		
		self.PCsAtivos[key]["control"]["queue_in"].put_nowait((Protocol.Control.SEND_CMD,cmd))
		
		textviewSaidaComando.props.buffer.props.text += entry.props.text + "\n"
		entry.props.text = ""
		
	
	#
	# Janela Shell
	#
	#####

	
def main():
	builder = Gtk.Builder()
	builder.add_from_file("controleGUI.glade")
	builder.connect_signals(MainHandler(builder))

	window = builder.get_object("janelaPrincipal")
	window.show_all()

	Gtk.main()

if __name__ == "__main__":
	main()
