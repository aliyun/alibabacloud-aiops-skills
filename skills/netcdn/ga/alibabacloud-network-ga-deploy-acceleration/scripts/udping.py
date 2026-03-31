#!/usr/bin/env python

import argparse
import socket
import sys
import time
import string
import random
import signal
import os

count=0
count_of_received=0
rtt_sum=0.0
rtt_min=99999999.0
rtt_max=0.0

def print_statistics():
    if count!=0 and count_of_received!=0:
        print('')
        print('--- ping statistics ---')
    if count!=0:
        print('%d packets transmitted, %d received, %.2f%% packet loss'%(count,count_of_received, (count-count_of_received)*100.0/count))
    if count_of_received!=0:
        print('rtt min/avg/max = %.2f/%.2f/%.2f ms'%(rtt_min,rtt_sum/count_of_received,rtt_max))

def signal_handler(sig, frame):
    print_statistics()
    os._exit(0)

def random_string(length):
    return ''.join(random.choice(string.ascii_letters+ string.digits ) for m in range(length))

parser = argparse.ArgumentParser(description='UDP ping tool for measuring UDP round-trip time')
parser.add_argument('dest_ip', help='Destination IP address or hostname')
parser.add_argument('dest_port', type=int, help='Destination port')
parser.add_argument('-c', '--count', type=int, default=0, help='Number of packets to send (0 = infinite, default: 0)')
parser.add_argument('-l', '--length', type=int, default=64, help='Payload length in bytes (default: 64)')
parser.add_argument('-i', '--interval', type=int, default=1000, help='Interval between packets in ms (default: 1000)')
args = parser.parse_args()

IP=socket.gethostbyname(args.dest_ip)
PORT=args.dest_port
LEN=args.length
INTERVAL=args.interval
MAX_COUNT=args.count

is_ipv6=0

if IP.find(":")!=-1:
    is_ipv6=1

if LEN<5:
    print("Payload length must be >= 5")
    exit(1)
if INTERVAL<50:
    print("Interval must be >= 50 ms")
    exit(1)

signal.signal(signal.SIGINT, signal_handler)

if not is_ipv6:
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
else:
    sock = socket.socket(socket.AF_INET6,socket.SOCK_DGRAM)

print("udping %s via port %d with %d bytes of payload"% (IP,PORT,LEN))
sys.stdout.flush()

while True:
    payload= random_string(LEN)
    sock.sendto(payload.encode(), (IP, PORT))
    time_of_send=time.time()
    deadline = time.time() + INTERVAL/1000.0
    received=0
    rtt=0.0

    while True:
        timeout=deadline - time.time()
        if timeout <0:
            break
        sock.settimeout(timeout)
        try:
            recv_data,addr = sock.recvfrom(65536)
            if recv_data== payload.encode()  and addr[0]==IP and addr[1]==PORT:
                rtt=((time.time()-time_of_send)*1000)
                print("Reply from",IP,"seq=%d"%count, "time=%.2f"%(rtt),"ms")
                sys.stdout.flush()
                received=1
                break
        except socket.timeout:
            break
        except :
            pass
    count+= 1
    if received==1:
        count_of_received+=1
        rtt_sum+=rtt
        rtt_max=max(rtt_max,rtt)
        rtt_min=min(rtt_min,rtt)
    else:
        print("Request timed out")
        sys.stdout.flush()

    if MAX_COUNT > 0 and count >= MAX_COUNT:
        print_statistics()
        break

    time_remaining=deadline-time.time()
    if(time_remaining>0):
        time.sleep(time_remaining)
