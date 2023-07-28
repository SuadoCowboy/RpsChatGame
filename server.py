import socket
import threading
from tools import print_and_log, create_data, receive_data, PREFIX

def create_command_data(data, command_name: str, is_private: bool=True, type: str='message'):
	return create_data(data, 'server', is_private, type, tobytes=False, command=command_name)

rps_requests = {} # {requester: opponent} -- their usernames
rps_games = [] # [ { requester: option(str), opponent: option(str) } ] -- their usernames

def rps_request(conn: socket.socket, opponent: str):
	if opponent not in server_info['clients_names']:
		return create_command_data(f'{opponent} is not on the server', 'rps', type='errorMissingOpponent')

	opponent_conn = find_connection_by_username(opponent)
	
	# create match
	if (opponent in rps_requests and rps_requests[opponent] == clients[conn][1]) or (clients[conn][1] in rps_requests and rps_requests[clients[conn][1]] == opponent):
		rps_games.append({ clients[conn][1]: None, opponent: None })
		rps_requests.pop(opponent)

		print_and_log(f'creating rps game for {clients[conn][1]} vs {opponent}')

		send(opponent_conn, clients[conn][1], type='commandRpsAccepted')
		send(conn, opponent, type='commandRpsAccepted')

		return
	else: # put in request
		rps_requests[clients[conn][1]] = opponent
		
		send(opponent_conn, clients[conn][1], type='commandRpsRequest')
		
		return create_command_data(f'request sent to {opponent}', 'rps')

rps_options = {'r':0,'p':1,'s':2}
def rps_logic(player1_name: str, player2_name: str, player1: str, player2: str):
	player1_choice = rps_options[player1]
	player2_choice = rps_options[player2]
	
	if player1_choice == 0 and player2_choice == 2:
		player2_choice = -1
	elif player1_choice == 2 and player2_choice == 0:
		player1_choice = -1

	if player1_choice > player2_choice:
		return (player1_name, player1, player2)
	elif player2_choice > player1_choice:
		return (player2_name, player2, player1)
	elif player1_choice == player2_choice:
		return -1

def rps_option(conn: socket.socket, client_username: str, option: str):
	for gameId, game in enumerate(rps_games):
		
		if client_username in game:
		
			game[client_username] = option
			
			for username in game.keys():
				if username != client_username:
					opponent_username = username
					break
			
			if game[client_username] and game[opponent_username]: # if they != None
				
				result = rps_logic(client_username, opponent_username, game[client_username], game[opponent_username])

				if result == -1:
					out = f'draw\nboth used /{game[client_username]}'
				
				elif result == None:
					send(conn, f'Waiting {opponent_username} to make a choice...')
					return
				else:
					out = f'{result[1]} beats {result[2]}\n{result[0]} won'
				
				send(find_connection_by_username(opponent_username), out)
				send(conn, out)

				rps_games.pop(gameId)
				
			return
	
	send(conn, 'You are not in a rps game.', type='errorNotInRpsGame')

def rps_rock(conn: socket.socket):
	rps_option(conn, clients[conn][1], 'r')

def rps_paper(conn: socket.socket):
	rps_option(conn, clients[conn][1], 'p')

def rps_scissors(conn: socket.socket):
	rps_option(conn, clients[conn][1], 's')

def find_connection_by_username(username: str):
	for client in clients:
		if clients[client][1] == username:
			return client

commands = {
	'rps': { 'function': rps_request, 'need_argument': True },
	'r': { 'function': rps_rock, 'need_argument': False },
	'p': { 'function': rps_paper, 'need_argument': False },
	's': { 'function': rps_scissors, 'need_argument': False }
}

def get_commands(_conn: socket.socket):
	out = ''
	for command_name in commands:
		out += command_name + '\n'
	
	return create_command_data(out[:-1], 'commands')

commands['commands'] = {'function':get_commands,'need_argument':False}

illegal_names = [PREFIX, 'server']

IP = socket.gethostbyname(socket.gethostname())
PORT = 5500

def sendall(data, sentby: str='server', type: str='message'):
	data = create_data(data, sentby, False, type)

	for client in clients:
		try:
			client.sendall(data)
		except Exception as e:
			print_and_log(f'[ERROR] triggered an exception while trying to send data to {clients[client][0]}:{clients[client][1]} => {e}')

def send(conn: socket.socket, data, sentby: str='server', type: str='message'):
	conn.sendall(create_data(data, sentby, True, type))

server_info = {'clients_connected':0,'clients_limit':5,'clients_names':[]}

clients = {} # {conn:[addr, client_name]}
def create_client(conn: socket.socket, addr):
	if server_info['clients_connected'] >= server_info['clients_limit']:
		send(conn, f'server limit reached ({server_info["clients_connected"]}/{server_info["clients_limit"]})', type='errorConnectionFailed')
		return
	else:
		send(conn, '', type='ok')

	threading.Thread(target=handle_client, args=(conn, addr)).start()

def disconnect_client(conn: socket.socket, client_username: str):
	clients.pop(conn)
	server_info['clients_connected'] -= 1
	
	if client_username == None:
		return
	
	server_info['clients_names'].remove(client_username)
	sendall(server_info, type='serverUpdate')
	sendall(f'{client_username} disconnected.')

def handle_client(conn: socket.socket, addr):
	try:
		with conn:
			print_and_log(f'{addr[0]}:{addr[1]} connected.')
			
			# first thing the client sends is his username
			client_username = receive_data(conn)['content']

			clients[conn] = [addr, client_username]
			server_info['clients_connected'] += 1
			
			if client_username in illegal_names:
				print_and_log(f'{addr[0]}:{addr[1]} tried to use \"{client_username}\" as username')
				
				send(conn, f'{client_username} is an illegal username', type='ErrorBadName')
				
				disconnect_client(conn, None)
				return

			elif client_username in server_info['clients_names']:
				print_and_log(f'{addr[0]}:{addr[1]} tried to use an already taken username: {client_username}')
				
				send(conn, 'name is already taken', type='ErrorBadName')
				
				disconnect_client(conn, None)
				return
			
			else:
				send(conn, 'name accepted', type='ok')
			
			print_and_log(f'{addr[0]}:{addr[1]} username is {client_username}')

			server_info['clients_names'].append(client_username)

			sendall(server_info, type='serverUpdate')

			while True:
				data = receive_data(conn)
				
				if not data: # triggered when client disconnects
					break
				
				if type(data['content']) == str:
					data['content'] = data['content'].strip()

				try:
					
					if data['is_private'] and data['content'].startswith(PREFIX): # check if it is a command
						command = data['content'][len(PREFIX):]

						args = ''
						if ' ' in command:
							command, args = command[:command.index(' ')], command[command.index(' ')+1:]
						
						if command not in commands:
							out = f'Unkown command: {command}'
							
							send(conn, out, type='errorUnknownCommand')
							
							raise Exception(out)
						
						if commands[command]['need_argument']:
							if not args:
								out = f'{command} requires arguments, no argument found.'
								
								send(conn, out, type='errorMissingArgument')
								
								raise Exception(out)
							
							out = commands[command]['function'](conn, args)
						else:
							out = commands[command]['function'](conn)
						
						if out: send(conn, out, type='commandOutput')
				
				except Exception as e:
					print_and_log(f'{addr[0]}:{addr[1]}@{client_username} error while trying to check for command => {type(e)} {e}')
				
				print_and_log(f'{addr[0]}:{addr[1]}@{client_username} sent: {data["content"]}')
				
				if not data['is_private']: sendall(data['content'], client_username)
	
	except Exception as e:
		print_and_log(f'{addr[0]}:{addr[1]}@{client_username} disconnected with an exception: {e}')
	
	disconnect_client(conn, client_username)
	
	print_and_log(f'{addr[0]}:{addr[1]}@{client_username} disconnected.')

# Internet addr family: AF_INET => IPv4
# protocol: SOCK_STREAM => TCP
print_and_log('starting server')
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
	s.bind((IP, PORT))
	
	try:
		while True:
			s.listen()
			conn, addr = s.accept()
			
			create_client(conn, addr)
	except KeyboardInterrupt:
		print_and_log('KeyboardInterrupt exception triggered, shuting down...')