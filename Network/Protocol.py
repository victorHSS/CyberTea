#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# PROTOCOLO UDP
class Discovery:
	
	DISCOVERY			=			b"\x00"
	REQUEST				=			b"\x01"
	STATIC_INFO			=			b"\x02"
	ACK					=			b"\x03"

## pra saber se esta alive + info mutavel
class Info:
	
	INFO				=			b"\x10"
	SCREEN				=			b"\x11"
	PROCESSES			=			b"\x12"
	ACK					=			b"\x15"


#PROTOCOLO TCP

class Control:
	
	CONNECT				=			b"\x20"
	DISCONNECT			=			b"\x21"
	
	READY				=			b"\x30"
	
	TURNON				=			b"\x32"
	REBOOT				=			b"\x33"
	SHUTDOWN			=			b"\x34"
	BLOCK_SYSTEM		=			b"\x35"
	OPEN_TRAY			=			b"\x36"
	
	SEND_MSG			=			b"\x37"
	
	GET_PROGRAM_LIST	=			b"\x40"
	BLOCK_PROGRAM		=			b"\x41"
	UNBLOCK_PROGRAM		=			b"\x42"
	KILL_PROGRAM		=			b"\x43"
	
	SEND_CMD			=			b"\x48"
	ANSWER_CMD			=			b"\x49"
	
	INSTALL_PKG			=			b"\x50"
	UNINSTALL_PKG		=			b"\x52"
	UPDATE_SYSTEM		=			b"\x53"
	
	RECV_LIST_FILES		=			b"\x60"
	SEND_LIST_FILES		=			b"\x61"
	
	BYE					=			b"\x99"









