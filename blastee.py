#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
import time

def mk_ack_pkt(src_mac, dst_mac, src_ip, dst_ip, sequence_num, payload):
    ethernet = Ethernet(src = src_mac, dst = dst_mac, ethertype = EtherType.SLOW)
    ip =  IPv4(src = src_ip, dst = dst_ip, protocol = IPProtocol.UDP)
    udp = UDP(src = 1357, dst = 2468)

    pkt = ethernet + ip + udp + RawPacketContents(sequence_num.to_bytes(4, 'big') + payload)
    return pkt 

def parse_pkt(pkt):
    payload = bytearray(pkt[RawPacketContents].data)
    log_debug("RAW PACKET CONTENTS SIZE: " + str(pkt[RawPacketContents].size()))
    start_raw = pkt[Ethernet].size()
    start_raw += pkt.get_header(IPv4).size()
    start_raw += pkt[UDP].size()
    sequence = int.from_bytes(bytes(payload[start_raw:start_raw + 4]), 'big')
    length = int.from_bytes(bytes(payload[start_raw + 4: start_raw + 6]), 'big')
    log_debug("RECEIVED PACKET SEQUENCE NUM: " + str(sequence))
    data = bytes(payload[start_raw + 6: start_raw + length])

    return sequence, data


def switchy_main(net):
    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    
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
            log_debug("I got a packet from {}".format(dev))
            log_debug("Pkt: {}".format(pkt))

            sequence, data = parse_pkt(pkt)
            ack = mk_ack_pkt(blastee_mac, mid_blastee_mac, blastee_ip, blaster_ip, sequence, data)
            net.send_packet(my_intf[0].name, ack)
            log_debug("ACK PACKET SEQUENCE NUM: " + str(sequence))


    net.shutdown()
