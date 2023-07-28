from datetime import datetime
import pickle
import socket

PREFIX = '/'

RECV_BUFSIZE = 1024
ENCODING = 'ascii'

def get_time():
	return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

log_output = ''
def print_and_log(out: str):
	global log_output

	out = f'[{get_time()}] {out}\n'
	
	print(out[:-1])
	
	log_output += out
	with open('log.txt', 'w') as f:
		f.write(log_output)

def receive_data(conn: socket.socket):
	data = conn.recv(RECV_BUFSIZE)
	return data if not data else pickle.loads(data, encoding=ENCODING)

def create_data(content, sentby: str, is_private, type: str, tobytes: bool=True, **others):
	out = {
		'content':content,
		'sentby':sentby,
		'sentdatetime':get_time(),
		'is_private':is_private,
		'type':type
	}

	if others:
		for item, value in others.items():
			out[item] = value
	
	return pickle.dumps(out) if tobytes else out