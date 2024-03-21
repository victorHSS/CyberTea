#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import copy
from collections import OrderedDict

#Exceção
class ConfError(IOError):
	pass

class KeyConfError(KeyError):
	pass

# TODO

# - considerar as secoes ao ler o arquivo de conf. Deixar as keys atreladas as secoes
# 		um dict de set {"[secao1]" : {"key1","key2"} , "[secao2]": {"key3", "key4"}}.
# 		e o dict __data normal
# 		o load teria que pegar a secao e o conjunto de key=value depois pegaria os key=value individualmente

# - criar uma classe especializada threaded-safe
class ConfHandler:
	
	def __init__(self, filename, autoflush=True):
		self.__data = OrderedDict()
		self.__newitem = set()
		self.__dirty = False
		self.__filename = filename
		self.autoflush = autoflush
		
		self.__loadConfFile()
		
		
	def __loadConfFile(self):
		#key_value_re = re.compile(r"^\s*(?P<key>\w+)\s*=\s*(?P<value>[\w\S]+)\s*$",re.MULTILINE)
		key_value_re = re.compile(r"^\s*(?P<key>\w+)\s*=\s*?(?P<value>.+)?(?<=\s)*$",re.MULTILINE)
		try:
			with open(self.__filename, mode="r", encoding="utf-8") as fconf:
				for match in key_value_re.finditer(fconf.read()):
					value = match.group("value")
					self.__data[match.group("key")] = value if value else ""
					
		except FileNotFoundError:
			raise ConfError(self.__filename)
		
	
	def __saveConfFile(self):
		
		def helper_sub(m):
			key, value = m.group(0).split("=")
			
			#se for comentario ignora
			if "#" in key:
				return m.group(0)
			
			#se chave foi apagada remove do arquivo
			if key not in self.__data:
				print("apagando "+key)
				return ""
			else:
				return key.strip() + "=" + self.__data[key]
			
		if not self.__dirty:
			return
			
		try:
			with open(self.__filename, mode="r+", encoding="utf-8") as fconf:
				text = fconf.read()
				
				for i in range(len(self.__data)):
					#text = re.sub(r"(#+\s*)?(\w)+\s*=\s*([\w\S])+", helper_sub, text)
					text = re.sub(r"(#+\s*)?(\w)+\s*=.*", helper_sub, text)
					text = re.sub(r"\n\n+", "\n", text)
					text = re.sub(r"\[", "\n[", text)
					
				
				fconf.seek(0)
				fconf.truncate()
			
				fconf.write(text.rstrip() + "\n")
				
				for key in self.__newitem:
					fconf.write(key + "=" + self.__data[key] + "\n")
				
			self.__newitem.clear()
			
			self.__dirty = False
			
		except FileNotFoundError:
			raise ConfError(self.__filename)
	
	flush = __saveConfFile
		
	def __getitem__(self, key):
		assert isinstance(key, str) , "Key must be string Type"
		return self.__data[key]
	
	
	def __setitem__(self, key, value):
		assert isinstance(key, str) , "Key must be string Type"
		assert isinstance(value, str) , "Value must be string Type"
		
		if key in self.__data and self.__data[key] == value:
			return
		
		if key not in self.__data:
			self.__newitem.add(key)
		
		self.__data[key] = value
		
		self.__dirty = True
		
		if self.autoflush:
			self.__saveConfFile()
			
	def __delitem__(self, key):
		try:
			del self.__data[key]
			self.__dirty = True
			
			if self.autoflush:
				self.__saveConfFile()
				
		except KeyError:
			raise KeyConfError(key)
	
	def __contains__(self, key):
		return key in self.__data
		
	@property
	def data(self):
		return copy.deepcopy(self.__data)
	
	@property
	def filename(self):
		return self.__filename
	
	@property
	def autoflush(self):
		return self.__autoflush
	
	@autoflush.setter
	def autoflush(self, autoflush):
		assert isinstance(autoflush, bool), "Must be BoolType"
		
		self.__autoflush = autoflush

	def __enter__(self):
		self.__autoflush = False
		return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		if exc_type is None:
			self.__saveConfFile()

if __name__ == "__main__":
	try:
	
		with ConfHandler("../client.conf") as client_conf:
			for key, value in client_conf.data.items():
				print("<{0}:{1}>".format(key,value))
			
			print("Alterando hostname para PC-02")
			client_conf["hostname"] = "PC-02"
			
			print(client_conf["hostname"])
			
			print("Alterando hostname para PC-01")
			client_conf["hostname"] = "PC-01"
			
			print(client_conf["hostname"])
			
			print("Adicionando novos atributos: readonly=False etc.")
			client_conf["readonly"]="False"
			client_conf["printscreen"]="True"
			
			#client_conf["clear"]="clear"
			print("Apagando atributos")
			del client_conf["clear"]
		
	except ConfError as cfile:
		print("Problema com arquivo de configuração {}".format(cfile))
	except KeyConfError as kcerror:
		print("Problema ao apagar chave {}".format(kcerror))
	
"""
		client_conf = ConfHandler("../client.conf")
		
		for key, value in client_conf.data.items():
			print("<{0}:{1}>".format(key,value))
		
		print("Alterando hostname para PC-02")
		client_conf["hostname"] = "PC-02"
		
		print(client_conf["hostname"])
		
		print("Alterando hostname para PC-01")
		client_conf["hostname"] = "PC-01"
		
		print(client_conf["hostname"])
		
		print("Adicionando novos atributos: readonly=False etc.")
		client_conf["readonly"]="False"
		client_conf["printscreen"]="True"
		
		#client_conf["clear"]="clear"
		print("Apagando atributos")
		del client_conf["clear"]
"""
	
	
	
	
	
	
	
	
