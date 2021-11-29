import select

from utils import *


class ChatServer(object):

    def __init__(self, host, port, backlog=5):
        self.client_amount = 0
        self.cmap = {}
        self.out = []
        self.one_to_one = []
        self.c_chat_room = []

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(backlog)

        print(f'Server starts listening to port: {port} ...')

    def oo_oneside_hang(self, sock):
        for chat in self.one_to_one:
            if chat[0] == sock:
                send(chat[1], "oo_fin")
                self.one_to_one.remove(chat)
            if chat[1] == sock:
                send(chat[0], "oo_fin")
                self.one_to_one.remove(chat)

    def leave_msg(self):
        if len(self.out) > 0:
            address_list, client_name_list = zip(
                *list(self.cmap.values()))
            self.send_all_new_online(client_name_list)

    def send_all_new_online(self, client_name_list):
        for output in self.out:
            send(output, f'sign_in: {str(client_name_list)}')

    def c_chat_room_leave_msg(self, sock):
        for chat_room in self.c_chat_room:
            if sock in chat_room[1]:
                chat_room[1].remove(sock)
                for member in chat_room[1]:
                    send(member, "mem_leave: " +
                         self.cmap[sock][1])
            break

    def run(self):
        inputs = [self.server]
        self.out = []
        running = True
        while running:
            try:
                readable, writeable, exceptional = select.select(
                    inputs, self.out, [])
            except select.error as e:
                break

            for sock in readable:
                if sock == self.server:
                    client, address = self.server.accept()
                    print(
                        f'Chat server: got connection {client.fileno()} from {address}')
                    client_name = receive(client).split('client name: ')[1]

                    inputs.append(client)
                    self.cmap[client] = (address, client_name)
                    self.client_amount += 1

                    address_list, client_name_list = zip(
                        *list(self.cmap.values()))
                    chat_room_names = []
                    if (len(self.c_chat_room) > 0):
                        chat_room_names, members = zip(*self.c_chat_room)
                    send(
                        client,
                        f'user: {str(address[0])}; active: {str(client_name_list)}; chatroom: {str(chat_room_names)};')
                    self.send_all_new_online(client_name_list)
                    self.out.append(client)

                else:
                    try:
                        datarecv = receive(sock)
                        # print(datarecv)
                        if datarecv:
                            if "oo_request" in datarecv:
                                oo_from = sock
                                oo_from_name = datarecv.split('oo_request: ')[
                                    1].split('::')[0]
                                oo_to_name = datarecv.split('oo_request: ')[
                                    1].split('::')[1]
                                for s in self.cmap:
                                    if self.cmap[s][1] == oo_to_name:
                                        oo_to_obj = s
                                jd = True
                                for chat in self.one_to_one:
                                    if chat[0] == oo_to_obj or chat[1] == oo_to_obj:
                                        jd = False
                                        break
                                for chat_room in self.c_chat_room:
                                    if oo_to_obj in chat_room[1]:
                                        jd = False
                                        break
                                if jd:
                                    self.one_to_one.append(
                                        (oo_from, oo_to_obj))
                                    send(oo_to_obj,
                                         f'oo_object: {oo_from_name}')
                                    send(
                                        oo_from, f'oo_object: {str(self.cmap[oo_to_obj][1])}')
                                else:
                                    send(oo_from, f'oo_reject')
                                jd = True

                            if "oo_msg" in datarecv:
                                for chat in self.one_to_one:
                                    if chat[0] == sock:
                                        send(chat[1], datarecv.replace(
                                            "Me", self.cmap[chat[0]][1]))
                                    if chat[1] == sock:
                                        send(chat[0], datarecv.replace(
                                            "Me", self.cmap[chat[1]][1]))

                            if "oo_fin" in datarecv:
                                for chat in self.one_to_one:
                                    if chat[0] == sock or chat[1] == sock:
                                        send(chat[0], "oo_fin")
                                        send(
                                            chat[0], f'sign_in: {str(client_name_list)}')
                                        send(chat[1], "oo_fin")
                                        send(
                                            chat[1], f'sign_in: {str(client_name_list)}')
                                        self.one_to_one.remove(chat)

                            if "create_chat_room" in datarecv:
                                if len(self.c_chat_room) > 0:
                                    chat_room_names, members = zip(*self.c_chat_room)
                                if self.cmap[sock][1] not in chat_room_names:
                                    self.c_chat_room.append(
                                        (self.cmap[sock][1], [sock]))
                                    send(sock, "chat_room_added")
                                    chat_room_names, members = zip(*self.c_chat_room)
                                    for output in self.out:
                                        send(
                                            output, f'add_chat_room: {str(chat_room_names)}')

                            if "join_chat_room" in datarecv:
                                chat_room_members = []
                                chat_room_name = datarecv.split('join_chat_room: ')[
                                    1]
                                for chat_room in self.c_chat_room:
                                    if chat_room_name.replace("Room by ", "") == chat_room[0]:
                                        chat_room[1].append(sock)
                                        for member in chat_room[1]:
                                            send(member, "new_mem: " +
                                                 self.cmap[sock][1])
                                            chat_room_members.append(
                                                self.cmap[member][1])
                                        break

                                send(sock, "chat_room_entered: " + chat_room_name.replace("Room by ",
                                                                                          "") + "; chat_room_member: " +
                                     str(chat_room_members))

                            if "quit_chat_room" in datarecv:
                                self.c_chat_room_leave_msg(sock)
                                send(sock, "quit_confirm")
                                send(sock, f'add_chat_room: {str(chat_room_names)}')

                            if "msg_group" in datarecv:
                                msg = datarecv.split('msg_group: ')[1].replace(
                                    "Me", self.cmap[sock][1])
                                for chat_room in self.c_chat_room:
                                    if sock in chat_room[1]:
                                        for member in chat_room[1]:
                                            if member != sock:
                                                send(
                                                    member, f'msg_group: {str(msg)}')
                                        break
                            if "inv_request" in datarecv:
                                address_list, client_name_list = zip(
                                    *list(self.cmap.values()))
                                send(sock, "invitee_list: " + str(client_name_list))

                            if "invitation" in datarecv:
                                invitee = datarecv.replace("invitation: ", "").split("::")[0]
                                for client in self.cmap:
                                    if self.cmap[client][1] == invitee:
                                        send(client,
                                             "get_invitation: " + datarecv.replace("invitation: ", "").split("::")[
                                                 1])

                        else:
                            inputs.remove(sock)
                            del self.cmap[sock]
                            self.oo_oneside_hang(sock)
                            self.out.remove(sock)
                            self.client_amount -= 1
                            self.leave_msg()
                            self.c_chat_room_leave_msg(sock)

                    except socket.error as e:
                        self.c_chat_room_leave_msg(sock)
                        inputs.remove(sock)
                        del self.cmap[sock]
                        self.oo_oneside_hang(sock)
                        self.out.remove(sock)
                        self.client_amount -= 1
                        self.leave_msg()


if __name__ == "__main__":
    host = "localhost"
    port = 9988

    server = ChatServer(host, port)
    server.run()
