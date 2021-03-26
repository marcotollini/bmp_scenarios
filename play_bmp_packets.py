import socket
import argparse

from scapy.supersocket import StreamSocket
import pickle
from build_packets import BMPSimPackets
from bmp import BMPHeader
import threading
from time import sleep
from random import randint
import ipaddress

class Client:
    def __init__(self, thread_index, collector_ip, collector_port, distributed_start, client_ip, wait_time, packets):
        self.thread_index = thread_index
        self.collector_ip = collector_ip
        self.collector_port = collector_port
        self.distributed_start = distributed_start
        self.client_ip = client_ip
        self.wait_time = wait_time
        self.packets = packets

        self.running = True

    def get_sleep(self):
        if len(self.wait_time) == 2:
            return randint(self.wait_time[0], self.wait_time[1])
        else:
            return self.wait_time[0]

    def run(self):
        if self.distributed_start != 0:
            sleep(randint(0, self.distributed_start))

        print('Connecting', self.thread_index, 'with ip', self.client_ip)

        s = socket.socket()
        s.bind((str(self.client_ip), 0))
        s.connect((self.collector_ip, self.collector_port))
        ss = StreamSocket(s, BMPHeader)

        packets = self.packets

        ss.send(packets.initialization)

        sleep(1)

        for p in packets.peers_up:
            ss.send(p)

        sleep(1)
        print('client', self.thread_index, 'running')

        while self.running:
            sleep(self.get_sleep())
            for p in packets.updates:
                ss.send(p)
            print('sent', self.thread_index)


# def send_packets(packets_pickle_name, ip="127.0.0.1", port=1790):

#     packets = pickle.load(open(packets_pickle_name, 'rb'))
#     # print(packets.initialization)
#     # return
#     s = socket.socket()
#     s.bind(('10.179.1.2', 0))
#     s.connect((ip, port))
#     ss = StreamSocket(s, BMPHeader)

#     ss.send(packets.initialization)
#     time.sleep(1)
#     for p in packets.peers_up:
#         ss.send(p)
#     time.sleep(1)
#     for p in packets.updates:
#         ss.send(p)
#     # while True:
#     #     pass

# if __name__ == '__main__':
#   fire.Fire(send_packets)

# https://stackoverflow.com/questions/4194948/python-argparse-is-there-a-way-to-specify-a-range-in-nargs
def required_length(nmin,nmax):
    class RequiredLength(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            if not nmin<=len(values)<=nmax:
                msg='argument "{f}" requires between {nmin} and {nmax} arguments'.format(
                    f=self.dest,nmin=nmin,nmax=nmax)
                raise argparse.ArgumentTypeError(msg)
            setattr(args, self.dest, values)
    return RequiredLength

def parse_args():
    parser = argparse.ArgumentParser(description='Stresstest BMP collector')
    parser.add_argument(
        '-c',
        '--collector-ip',
        default='127.0.0.1',
        dest="collector_ip",
        type=str,
        help="IP of the BMP collector",
    )

    parser.add_argument(
        '-p',
        '--collector-port',
        default=1790,
        dest="collector_port",
        type=int,
        help="Port of the BMP collector",
    )

    parser.add_argument(
        '-S',
        '--start-ip',
        dest="start_ip",
        type=str,
        required=True,
        help="First IP to use as a client",
    )

    parser.add_argument(
        '-F',
        '--prefix',
        dest="prefix",
        type=str,
        required=True,
        help="Prefix assigned to the interface",
    )

    parser.add_argument(
        '-C',
        '--number-clients',
        dest="number_clients",
        type=int,
        required=True,
        help="First IP to use as a client",
    )

    parser.add_argument(
        '-d',
        '--distributed-start',
        dest="distributed_start",
        type=int,
        default=0,
        help="If 0, connect all the clients together, else randomly wait distributed-start seconds before connecting a client",
    )

    parser.add_argument(
        '-D',
        '--test-duration',
        dest="test_duration",
        type=int,
        default=0,
        help="If 0, never stop the test, else stop the test after test-duration seconds",
    )

    parser.add_argument(
        '-P',
        '--packets-file',
        dest="packets_file",
        type=str,
        required=True,
        help="Path to the packet file generated via build_scenarios.py",
    )

    parser.add_argument(
        '-w',
        '--wait-time',
        dest="wait_time",
        nargs='+',
        action=required_length(1, 2),
        required=True,
        type=int,
        help="An integer for a static sleep, or a range (two numbers) to generate a uniormily distributed random number that is used to sleep",
    )

    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    packets = pickle.load(open(args.packets_file, 'rb'))

    start = ipaddress.IPv4Address(args.start_ip)
    network = ipaddress.IPv4Network(f'{args.start_ip}/{args.prefix}', strict=False)

    ip_it = network.hosts()
    ip = next(ip_it)
    while ip < start:
        ip = next(ip_it)
        continue

    clients = []
    for i in range(1, args.number_clients + 1):
        client = Client(i, args.collector_ip, args.collector_port, args.distributed_start, ip, args.wait_time, packets)
        thread = threading.Thread(target=client.run)
        thread.start()
        clients.append((client, thread))
        ip = next(ip_it)

    try:
        if args.test_duration == 0:
            while True:
                sleep(60*60*24)
        else:
            sleep(args.test_duration)
        print('stopping')
    except KeyboardInterrupt:
        print('control+c - Stopping')
    finally:
        for (client, thread) in clients:
            client.running = False

        for (client, thread) in clients:
            thread.join()

        print('all done :)')

if __name__ == '__main__':
  main()