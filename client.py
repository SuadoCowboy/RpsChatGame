import socket
import sys
from tools import create_data, receive_data, PREFIX
import threading

USERNAME = sys.argv[1]

IP = socket.gethostbyname(socket.gethostname())
PORT = 5500
ADDR = (IP, PORT)

def update_server_info():
	print(f'Users: {server_info["clients_connected"]}/{server_info["clients_limit"]}')
	
	users_names = ''
	for client in server_info['clients_names']:
		users_names += client+'\n'
	
	print(users_names[:-1])
	del(users_names)

def send(conn: socket.socket, data, is_private: bool=False, type: str='message'):
	conn.sendall(create_data(data, '', is_private, type))

def look_for_server_data(conn: socket.socket, badtype: str, goodtype: str):
	'''
	only returns after server sent something related to what the client is looking for
	'''
	while True:
		data = receive_data(conn)

		if data['sentby'] == 'server':
			if data['type'] == badtype:
				return (data, False)
			
			elif data['type'] == goodtype:
				return (data, True)

def print_error(sentdatetime, message):
	print(f'[{sentdatetime}][ERROR] SERVER : {message}')

def receive_loop(conn: socket.socket):
	global server_info
	
	try:
		while True:
		
			data = receive_data(conn)

			if data['type'] == 'message':
				if data['sentby'] == USERNAME:
					print(f'[{data["sentdatetime"]}][MESSAGE] {data["sentby"]}(You) : {data["content"]}')
				else:
					print(f'[{data["sentdatetime"]}][MESSAGE] {data["sentby"]} : {data["content"]}')
			
			if data['sentby'] == 'server':
				if data['type'] == 'serverUpdate':
					server_info = data['content']
					update_server_info()

				elif data['type'].startswith('error'):
					print_error(data["sentdatetime"], data["content"])
				
				elif data['type'].startswith('command'):

					if data['type'] == 'commandOutput':
						command_data = data['content']

						if command_data['type'] == 'message':
							print(command_data['content'])
						
						elif command_data['type'].startswith('error'):
							print_error(command_data['sentdatetime'], command_data['content'])
					
					elif data['type'] == 'commandRpsRequest':
						print(f'{data["content"]} is requesting you for a rps game, type \"{PREFIX}rps {data["content"]}\" to accept.')

					elif data['type'] == 'commandRpsAccepted':
						print(f'accepted rps request from {data["content"]}\ntype \"{PREFIX}r\", \"{PREFIX}p\" or \"{PREFIX}s\" to select your object')

	except KeyboardInterrupt: pass

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
	s.connect(ADDR)
	
	data, ok = look_for_server_data(s, 'errorConnectionFailed', 'ok')
	if not ok:
		print(data['content'])
		quit()

	send(s, USERNAME)

	data, ok = look_for_server_data(s, 'ErrorBadName', 'ok')
	if not ok:
		print(f'\"{USERNAME}\" is not an allowed name for the server: {data["content"]}')
		quit()
	else:
		print('name accepted by server')
	
	server_info = look_for_server_data(s, 'serverUpdate', 'serverUpdate')[0]['content'] # it doesn't matter if it's ok in that case

	update_server_info()

	receive_thread = threading.Thread(target=receive_loop, args=(s,))
	receive_thread.start()
	while True:
		message = input('')
		if message:
			send(s, message, True if message.startswith(PREFIX) else False)