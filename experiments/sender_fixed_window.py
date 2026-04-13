#!/usr/bin/env python3
from monitor import Monitor
import sys
import socket
# Config File
import configparser

if __name__ == '__main__':
	#print("Sender starting up!")
	config_path = sys.argv[1]

	send_monitor = Monitor(config_path, 'sender')

	cfg = configparser.RawConfigParser(allow_no_value=True)
	cfg.read(config_path)

	receiver_id = int(cfg.get('receiver', 'id'))
	file_to_send = cfg.get('nodes', 'file_to_send')
	max_packet_size = int(cfg.get('network', 'MAX_PACKET_SIZE'))
	link_bandwidth = int(cfg.get('network', 'LINK_BANDWIDTH'))
	chunk_size = 900
	prop_delay = float(cfg.get('network', 'PROP_DELAY'))

	timeout = max(0.2, 4 * prop_delay + 0.05)
	send_monitor.socketfd.settimeout(timeout)
	#print(f"Snder: timeoeut set to {timeout:.3f}s")
	bandwidth_bytes = link_bandwidth / 8
	rtt = 2 * prop_delay
	bdp  = bandwidth_bytes * rtt
	window_size = 1
    #print(f"sender using fixed window = {window_size}")
	with open(file_to_send, 'rb') as f:
		file_data = f.read()

	chunks = [file_data[i:i + chunk_size] for i in range(0, len(file_data), chunk_size)]
	packets = [b"DATA|" + str(i).encode() + b"|" + chunks[i] for i in range(len(chunks))]
	
	base = 0
	next_seq = 0
	last_ack = -1
	dup_count_ack = 0

	while base < len(chunks):
		while next_seq < base + window_size and next_seq < len(packets):
			#print(f"Sender: sending packet {next_seq}")
			send_monitor.send(receiver_id, packets[next_seq])
			next_seq += 1

		try:
			addr, ack = send_monitor.recv(max_packet_size)
			if ack is None:
				continue
			parts = ack.split(b"|")

			if parts[0] == b"ACK":
				ack_num = int(parts[1])
				#print(f"Sender: got ACK for packet {ack_num}")
				if ack_num > last_ack:
					last_ack = ack_num
					dup_count_ack = 0
					base = ack_num + 1
				elif ack_num == last_ack:
					dup_count_ack += 1
					#print(f"Sender - dpupliczte ACK count = {dup_count_ack}")
					if dup_count_ack >= 3 and base < len(packets):
						#print(f"Sender- fast retransmit packet {base}")
						send_monitor.send(receiver_id, packets[base])
						dup_count_ack = 0

		except socket.timeout:
			#print("Sender: timeout- retransmting window")
			send_monitor.send(receiver_id, packets[base])
			next_seq = base + 1
			dup_count_ack = 0

	# send the end packet
	end_seq = len(chunks)
	end_packet = b"END|" + str(end_seq).encode()

	while True:
		#print("Sender- sending END")
		send_monitor.send(receiver_id, end_packet)
		try:
			addr, ack = send_monitor.recv(max_packet_size)
			if ack == b"ACK_END|" + str(end_seq).encode():
				#print("Sender- got END ACK")
				break
		except socket.timeout:
			pass
			#print("Sender-  timeout on END, resending")

	send_monitor.send_end(receiver_id)
