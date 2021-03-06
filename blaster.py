#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from random import randint
import time

def print_output(total_time, num_ret, num_tos, throughput, goodput):
    print("Total TX time (s): " + str(total_time))
    print("Number of reTX: " + str(num_ret))
    print("Number of coarse TOs: " + str(num_tos))
    print("Throughput (Bps): " + str(throughput))
    print("Goodput (Bps): " + str(goodput))

def parse_params(filename):
    file = open(filename, "r")
    params = file.readline().split(" ")
    
    num = ""
    length = ""
    sender_window = ""
    timeout = ""
    recv_timeout = ""

    for i in range(0, len(params), 2):
        if 'n' in params[i]:
            num = params[i + 1]
        elif 'l' in params[i]:
            length = params[i + 1]
        elif 'w' in params[i]:
            sender_window = params[i + 1]
        elif 't' in params[i]:
            timeout = params[i + 1]
        elif 'r' in params[i]:
            recv_timeout = params[i + 1]

    return int(num), int(length), int(sender_window), int(timeout), int(recv_timeout)

def mk_pkt(src_mac, dst_mac, src_ip, dst_ip, sequence_num, payload_length):
    ethernet = Ethernet(src = src_mac, dst = dst_mac, ethertype = EtherType.SLOW)
    ip =  IPv4(src = src_ip, dst = dst_ip, protocol = IPProtocol.UDP)
    udp = UDP(src = 1357, dst = 2468)
    payload = [0xab] * payload_length

    pkt = udp + ip + ethernet + RawPacketContents(sequence_num.to_bytes(4, 'big') + payload_length.to_bytes(2, 'big') + bytes(payload))
    return pkt

def parse_pkt(pkt):
    payload = bytearray(pkt[RawPacketContents].to_bytes())
    sequence = int.from_bytes(bytes(payload[0:4]), 'big', signed = False)
    log_debug("RECEIVED PACKET SEQUENCE NUM: " + str(sequence))
    return sequence 


def switchy_main(net):
    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]
    
    blaster_mac = '10:00:00:00:00:01'
    mid_blaster_mac = '20:00:00:00:00:01'
    mid_blastee_mac = '20:00:00:00:00:02'
    blastee_mac = '40:00:00:00:00:01'
    blaster_ip = '192.168.100.1'
    blastee_ip = '192.168.200.1'
    mid_blaster_ip = '192.168.100.2'
    mid_blastee_ip = '192.168.200.2'

    num, length, sender_window, timeout, recv_timeout = parse_params("./blaster_params.txt")

    lhs = 1
    rhs = 1

    timeout_queue = []

    start_time = -1
    end_time = -1
    reTX = 0

    while True:
        gotpkt = True
        try:
            #Timeout value will be parameterized!
            timestamp,dev,pkt = net.recv_packet(recv_timeout)
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet")
            end_time = time.time() * 1000
            sequence = parse_pkt(pkt)
            for pending_pkt in timeout_queue:
                if pending_pkt[0] == sequence:
                    timeout_queue.remove(pending_pkt)
                    break

            if len(timeout_queue) == 0 and rhs > num:
                break
                
            elif sequence == lhs:
                if len(timeout_queue) > 0:
                    lhs = timeout_queue[0][0]
                else:
                    lhs = rhs

        else:
            log_debug("Didn't receive anything")

            #check timeout_queue
            timeout = False
            curr_time = time.time() * 1000

            for pending_pkt in timeout_queue:
                if pending_pkt[1] - curr_time >= timeout:
                    pending_pkt[1] = curr_time
                    pkt = mk_pkt(blaster_mac, mid_blaster_mac, blaster_ip, blastee_ip, pending_pkt[0], length)
                    net.send_packet(my_intf[0].name, pkt)
                    log_debug("SENDING PACKET SEQUENCE NUM: " + str(pending_pkt[0]))
                    reTX += 1
                    timeout = True
                    break

            if timeout:
                continue
            '''
            Creating the headers for the packet
            '''

            if sender_window > rhs - lhs and rhs <= num:
                pkt = mk_pkt(blaster_mac, mid_blaster_mac, blaster_ip, blastee_ip, rhs, length)
                net.send_packet(my_intf[0].name, pkt)
                log_debug("SENDING PACKET SEQUENCE NUM: " + str(rhs))
                if (start_time < 0):
                    start_time = time.time() * 1000
                timeout_queue.append((rhs, time.time() * 1000))
                rhs += 1


            '''
            Do other things here and send packet
            '''
    
    total_time = end_time - start_time
    throughput = (length * (num + reTX)) / total_time
    goodput = length * num / total_time
    print_output(total_time, reTX, reTX, throughput, goodput)        

    net.shutdown()
