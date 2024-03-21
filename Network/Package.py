#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct

class DataNotReady(OSError):
	pass

class DataError(OSError):
	pass

def genTCPPackage(msg : bytes):
	return TCPPackage(msg[:1],msg[5:],msg[1:5])

class TCPPackage():
	
	def __init__(self, type_msg : bytes, data=b"", isize=None):
		#assert pkg len menorigual que buffer
		idata_size = struct.pack("!I",len(data)) if not isize else isize
		self.__msg = type_msg + idata_size + data
	
	@property
	def type_msg(self):
		return self.__msg[:1]
	
	@property
	def msg(self):
		return self.__msg
	
	@property
	def data(self):
		return self.__msg[5:]
	
	@property
	def datalen(self):
		return struct.unpack("!I", self.__msg[1:5])[0]
	
	@property
	def bdatalen(self):
		return self.__msg[1:5]
	
	def __len__(self):
		return len(self.__msg)

class UDPRePackager():
	# classe para juntar os pedaços e entregar os dados originais
	def __init__(self):
		self.__ready = False
		self.__lost = False
		self.__tsize = -1
		self.__data = set()
		self.__info = None
		
	def loads(self, pkg):
		pkg_len = len(pkg.data)
		if pkg.isAtomic:
			self.__info = pkg.data
			self.__ready = True
		elif pkg.isHead:
			self.__data = {(0,pkg_len,pkg.data)}
			#self.__data = [(0,pkg.data)]
			self.__tsize = pkg.size
			#self.__asize = len(pkg.data)
		elif pkg.isBody:
			self.__data.add((pkg.size,pkg_len,pkg.data))
			#self.__data.append((pkg.size,pkg.data))
			#self.__asize += len(pkg.data)
		elif pkg.isTail:
			self.__data.add((pkg.size,pkg_len,pkg.data))
			#self.__asize += len(pkg.data)
			
			tsize = sum(s[1] for s in self.__data)
			
			#if self.__asize == self.__tsize:
			if tsize == self.__tsize:
				orgdata = sorted(self.__data,key=(lambda x: x[0]))
				#orgdata = sorted(self.__data)
				data = bytearray()
				for d in orgdata:
					data += d[2]
					#data += d[1]
				
				self.__info = bytes(data)
				self.__ready = True
			else:
				self.__lost = True
				self.__ready = True
				
	@property
	def ready(self):
		return self.__ready
	
	@property
	def lost(self):
		return self.__lost	
	
	@property
	def info(self):
		if not self.__ready:
			raise DataNotReady("Info is Not Ready Yet!")
		if self.__lost:
			raise DataError("Info is Corrupted! Retry!")
			
		return self.__info

class UDPPackage():
	def __init__(self, msg):
		self.__msg = msg
	
	@property
	def isHead(self):
		return True if self.__msg[12] == 0 else False
	
	@property
	def isBody(self):
		return True if self.__msg[12] == 1 else False
	
	@property
	def isTail(self):
		return True if self.__msg[12] == 2 else False
	
	@property
	def isAtomic(self):
		return True if self.__msg[12] == 3 else False
	
	@property
	def identity(self):
		ident = str(struct.unpack("!11s",self.__msg[1:12])[0], encoding="utf-8")
		return (ident[:6],ident[6:])
	
	@property
	def size(self):
		return struct.unpack("!I",self.__msg[13:17])[0]
	
	@property
	def data(self):
		return self.__msg[17:]
	
	@property
	def type_msg(self):
		return self.__msg[:1]
	
	@property
	def msg(self):
		return self.__msg

class UDPPackageGenerator():
	
	def __init__(self, type_msg : bytes, ident : tuple, BUFFER : int, data=None):
		self.__header_size = 1 + 11 + 1 + 4 # type + ident + nid + size
		self.__payload_size = BUFFER - self.__header_size
		
		self.__type_msg = type_msg
		self.__data = data if data else b"\x00" * (32 - self.__header_size)
		self.__len = len(data) if data else 0
		
		self.__iident = struct.pack("!11s",bytes(ident[0]+ident[1], encoding="utf-8"))
		self.__ilen = struct.pack("!I",self.__len)
		
		self.__nid0 = struct.pack("!B",0)
		self.__nid1 = struct.pack("!B",1)
		self.__nid2 = struct.pack("!B",2)
		self.__nid3 = struct.pack("!B",3)
	
	def packages(self):
		if self.__len <= self.__payload_size:
			msg = self.__type_msg + self.__iident + self.__nid3 + self.__ilen + self.__data
			yield msg
		
		else:
			msg = self.__type_msg + self.__iident + self.__nid0 + self.__ilen + self.__data[:self.__payload_size]
			yield msg
			for i in range(self.__payload_size, self.__len, self.__payload_size):
				ii = struct.pack("!I",i)
				msg = self.__type_msg + self.__iident + (self.__nid1 if self.__len - i > self.__payload_size else self.__nid2) + ii + self.__data[i:i+self.__payload_size]
				yield msg
	
	__iter__=packages

