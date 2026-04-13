#!/usr/bin/env python3
from monitor import Monitor
import sys
import socket
#Config File
import configparser

if __name__ == '__main__':
	print("Sender starting up!")
	config_path = sys.argv[1]

	#Initialize sender monitor
	send_monitor = Monitor(config_path, 'sender')
	
	#Parse config file
	cfg = configparser.RawConfigParser(allow_no_value=True)
	cfg.read(config_path)

	receiver_id = int(cfg.get('receiver', 'id'))
	file_to_send = cfg.get('nodes', 'file_to_send')
	max_packet_size = int(cfg.get('network', 'MAX_PACKET_SIZE'))
	chunk_size = 900
	send_monitor.socketfd.settimeout(0.5)
	with open(file_to_send, 'rb') as f:
		file_data = f.read()
	chunks = [file_data[i:i + chunk_size] for i in range(0, len(file_data), chunk_size)]

	seq = 0
	#llop through each cfhunk and send reliably : stop and wait
	for chunk in chunks:
		packet = b"DATA|" + str(seq).encode() + b"|" + chunk
		while True:
			print(f"Sender: sending packet {seq}")
			#send packet
			send_monitor.send(receiver_id, packet)
			try:
				#wait for ACK
				addr, ack = send_monitor.recv(max_packet_size)
				#expected format of ack
				expected_ack = b"ACK|" + str(seq).encode()
				#if ack is goof then next packet 
				if ack == expected_ack:
					print(f"Sender: got ACK for packet {seq}")
					break
				else:
					#wrong ack means ressed 
					print(f"Sender: unexpected ACK {ack}, resending packet {seq}")
			except socket.timeout:
				#timing issue so resend 
				print(f"Sender: timeout on packet {seq}, resending")
		seq += 1
	#send teh end packet
	end_packet = b"END|" + str(seq).encode()
	while True:
		print("Sender: sending END")
		send_monitor.send(receiver_id, end_packet)
		try:
			addr, ack = send_monitor.recv(max_packet_size)
			#expected end AXCK format
			expected_end_ack = b"ACK_END|" + str(seq).encode()
			if ack == expected_end_ack:

				print("Sender: got END ACK")
				break
			else:
				print(f"Sender: unexpected END ACK {ack}, resending END")
		except socket.timeout:
			print("Sender: timeout on END, resending")
	#notify that monitor transmission is complete 
	send_monitor.send_end(receiver_id)