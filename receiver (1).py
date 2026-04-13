#!/usr/bin/env python3

from monitor import Monitor

import sys

#Config File

import configparser


if __name__ == '__main__':

	#print("Receiver starting up!")

	config_path = sys.argv[1]


	#Intialize send monitor

	recv_monitor = Monitor(config_path, 'receiver')

	

	#Parse config file

	cfg = configparser.RawConfigParser(allow_no_value=True)

	cfg.read(config_path)

	sender_id = int(cfg.get('sender', 'id'))

	write_location = cfg.get('receiver', 'write_location')

	max_packet_size = int(cfg.get('network', 'MAX_PACKET_SIZE'))

	expected_seq = 0

	#open output filr in the binary write mdoe 

	ooo_buffer = {}

	with open(write_location, 'wb') as f:

		while True:

			#recieve packet from sender

			addr, packet = recv_monitor.recv(max_packet_size)

			if packet is None:

				continue

			#split packet into type, sequence number, and payload

			parts = packet.split(b"|", 2)

			pkt_type = parts[0]

			if pkt_type == b"DATA":

				seq = int(parts[1])

				payload = parts[2]

				# if pac has expecrred seqeunce number then accept it 

				if seq == expected_seq:

					#print(f"Receiver: got expected packet {seq}")

					f.write(payload)

					#send ACXK for correctly recieved oacket 

					expected_seq += 1

					while expected_seq in ooo_buffer:

						#print(f"Reicevier: delivering buffered packet {expected_seq}")

						f.write(ooo_buffer.pop(expected_seq))

						expected_seq += 1

					recv_monitor.send(sender_id, b"ACK|" + str(expected_seq - 1).encode())

				elif seq > expected_seq:

					if seq not in ooo_buffer:

						#print(f"Reieciever: buffering out of order packet {seq} (expected {expected_seq})")

						ooo_buffer[seq] = payload

						recv_monitor.send(sender_id, b"ACK|" + str(expected_seq -1).encode())


				else:

					#packet duplicated or out of order 

					#print(f"Receiver: got unexpected packet {seq}, expected {expected_seq}")

					#resend ACK for last correctly recieved packet 

					recv_monitor.send(sender_id, b"ACK|" + str(expected_seq - 1).encode())

			elif pkt_type == b"END":

				seq = int(parts[1])

				#print("Receiver: got END")

				recv_monitor.send(sender_id, b"ACK_END|" + str(seq).encode())

				break

	#notify montior thar transfer is fully complete 

	recv_monitor.recv_end(write_location, sender_id)
