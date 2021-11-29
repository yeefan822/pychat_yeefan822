import socket
import pickle
import struct
import codecs



def send(channel, *args):
    encode = codecs.encode(str(args), 'rot_13')
    args = eval(encode)
    buffer = pickle.dumps(args)
    value = socket.htonl(len(buffer))
    size = struct.pack("L", value)
    channel.send(size)
    channel.send(buffer)


def receive(channel):
    size = struct.calcsize("L")
    size = channel.recv(size)
    try:
        size = socket.ntohl(struct.unpack("L", size)[0])
    except struct.error as e:
        return ''
    buf = ""
    while len(buf) < size:
        buf = channel.recv(size - len(buf))

    return codecs.encode(pickle.loads(buf)[0],'rot_13')
