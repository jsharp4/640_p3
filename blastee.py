#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
import time

def mk_ack_pkt(src_mac, dst_mac, src_ip, dst_ip, sequence_num, payload):
    ethernet = Ethernet(src = blaster_mac, dst = middlebox_mac, ethertype = EtherType.Slow)
    ip =  IPv4(src = blaster_ip, dst = blastee_ip, protocol = IPProtocol.UDP)
    udp = UDP(src = '1357', dst = '2468')
    payload = [0xab] * payload_length

    pkt = ethernet + ip + udp + RawPacketContents(sequence_num.to_bytes(4, 'big') + payload_length.to_bytes(2, 'big') + payload.to_bytes(payload_length, 'big'))
    return pkt 

def parse_pkt(pkt):
    part_payload = bytearray(pkt[RawPacketContents].to_bytes(6, 'big'))
    sequence = int.from_bytes(part_payload[0:4], 'big')
    length = int.from_bytes(part_payload[4:6], 'big')

    full_payload = bytearray(pkt[RawPacketContents].to_bytes(6 + length, 'big'))
    data = full_payload[6:length].to_bytes(8, 'big')

    return sequence, data


def switchy_main(net):
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]

    blaster_mac = '10:00:00:00:00:{:02x}'
    middlebox_mac = '20:00:00:00:00:{:02x}'
    blastee_mac = '40:00:00:00:00:{:02x}'

    blaster_ip = '192.168.100.1/30'
    blastee_ip = '192.168.200.1/30'
    mid_blaster_ip = '192.168.100.2/30'
    mid_blastee_ip = '192.168.200.2/30'
    
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
            ack = mk_ack_pkt(blastee_mac, middlebox_mac, blastee_ip, blaster_ip, sequence, data)
            net.send_packet(blastee_mac, ack)


    net.shutdown()
