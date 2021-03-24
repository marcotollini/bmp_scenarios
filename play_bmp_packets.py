import fire
import socket
from scapy.supersocket import StreamSocket
import pickle
from build_packets import BMPSimPackets
import time
from bmp import BMPHeader


def send_packets(packets_pickle_name, ip="127.0.0.1", port=1790):

    packets = pickle.load(open(packets_pickle_name, 'rb'))
    s = socket.socket()
    s.connect((ip, port))
    ss = StreamSocket(s, BMPHeader)

    ss.send(packets.initialization)
    time.sleep(1)
    for p in packets.peers_up:
        ss.send(p)
    time.sleep(1)
    for p in packets.updates:
        ss.send(p)
    while True:
        pass

if __name__ == '__main__':
  fire.Fire(send_packets)



