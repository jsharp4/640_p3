#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
import random
import time

def drop(percent):
    return random.randrange(100) < percent

def parse_params(filename):
    file = open(filename, "r")
    params = file.readline().split(" ")
    
    seed = ""
    prob = ""

    for i in range(0, len(params), 2):
        if 's' in params[i]:
            seed = params[i + 1]
        elif 'p' in params[i]:
            prob = params[i + 1]

    return int(seed), int(prob)

def switchy_main(net):

    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]

    # random.seed(random_seed) #Extract random seed from params file
    # 
    seed, prob = parse_params('./middlebox_params.txt')
    random.seed(seed)
    
    blaster_mac = '10:00:00:00:00:01'
    mid_blaster_mac = '20:00:00:00:00:01'
    mid_blastee_mac = '20:00:00:00:00:02'
    blastee_mac = '40:00:00:00:00:01'
    blaster_ip = '192.168.100.1'
    blastee_ip = '192.168.200.1'
    mid_blaster_ip = '192.168.100.2'
    mid_blastee_ip = '192.168.200.2'

    while True:
        gotpkt = True
        try:
            timestamp,dev,pkt = net.recv_packet()
            log_debug("Device is {}".format(dev))
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet {}".format(pkt))

        if dev == "middlebox-eth0":
            log_debug("Received from blaster")
            '''
            Received data packet
            Should I drop it?
            '''
            drop_pkt = drop(prob)
            '''
            If not, modify headers & send to blastee
            '''
            if not drop_pkt:
                pkt[Ethernet].dst = blastee_mac
                pkt[Ethernet].src = mid_blastee_mac
                udp = pkt[UDP]
                ip = pkt[IPv4]
                net.send_packet("middlebox-eth1", udp + ip + pkt)


        elif dev == "middlebox-eth1":
            log_debug("Received from blastee")
            '''
            Received ACK
            Modify headers & send to blaster. Not dropping ACK packets!
            net.send_packet("middlebox-eth0", pkt)
            '''
            pkt[Ethernet].dst = blaster_mac
            pkt[Ethernet].src = mid_blaster_mac
            udp = pkt[UDP]
            ip = pkt[IPv4]
            net.send_packet("middlebox-eth0", udp + ip + pkt)
        else:
            log_debug("Oops :))")

    net.shutdown()
