import sys
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QListWidgetItem, QMessageBox, QWidget, QPushButton, QHBoxLayout, QVBoxLayout, \
    QLineEdit, QLabel, \
    QListWidget, QTextBrowser
from PyQt5.QtCore import Qt, pyqtSignal, QCoreApplication
import threading
import time
from utils import *

stop_thread = False


class Client:

    def __init__(self, name, port=9988, host="localhost"):
        self.name = name
        self.host = host
        self.port = port
        self.connect_status = False

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, self.port))
            print(f'Now successfully connected to chat server@ port {self.port}')
            self.connect_status = True

            # Send the name of client to server.
            send(self.sock, 'client name: ' + self.name)
            # Receive data from server.
            datarecv = receive(self.sock)
            online_ad = datarecv.split('user: ')[1]
            self.mem_list = list(online_ad.split('; active: ')[1].split('; chatroom: ')[0].replace(
                "\'", "").replace(",", "").replace("(", "").replace(")", "").split(" "))

            self.chat_room_list = list(online_ad.split('; chatroom: ')[1].replace(
                "\'", "").replace(",", "").replace("[", "").replace("]", "").replace("(", "").replace(")", "").replace(
                ";", "").split(" "))

            if self.chat_room_list[0] == '':
                self.chat_room_list = []
        # Catch exception.
        except socket.error as e:
            print(f'Failed to connect to chat server @ port {self.port}')
            sys.exit(1)

    def set_waiting_chat_room(self, waiting_chat_room):
        self.waiting_chat_room = waiting_chat_room

    def set_oto(self, oto):
        self.oto = oto

    def update_chatroom(self,chatroom):
        self.chat_room_list.remove(chatroom)
        self.waiting_chat_room.chat_room_list.remove(self.chat_room)

    def set_chat_room(self, chat_room):
        self.chat_room = chat_room

    def run_waiting_chat_room(self):
        self.at_waiting_chat_room = True
        # When the client is in the waiting chat_room, keep hearing from server.
        while self.at_waiting_chat_room:
            datarecv = receive(self.sock)
            # print(datarecv)
            if "sign_in" in datarecv:
                self.mem_list = list(datarecv.split('sign_in: ')[1].replace(
                    "\'", "").replace(",", "").replace("(", "").replace(")", "").split(" "))
                self.waiting_chat_room.update_client_list()
            if "oo_object" in datarecv:
                self.at_waiting_chat_room = False
                self.waiting_chat_room.oto_sig.emit(datarecv.split('oo_object: ')[1])
            if "oo_reject" in datarecv:
                self.waiting_chat_room.oto_refuse_sig.emit()
            if "chat_room_added" in datarecv:
                self.at_waiting_chat_room = False
                self.chat_room_list.append(self.name)
                self.waiting_chat_room.chat_room_created_sig.emit()
            if "chat_room_entered" in datarecv:
                self.at_waiting_chat_room = False
                self.waiting_chat_room.chat_room_joined_sig.emit(
                    datarecv.split('chat_room_entered: ')[1])
            if "add_chat_room" in datarecv:
                self.chat_room_list = list(datarecv.split('add_chat_room: ')[1].replace(
                    "\'", "").replace("[", "").replace("]", "").replace(",", "").replace("(", "").replace(")",
                                                                                                          "").replace(
                    ";", "").split(" "))
                self.waiting_chat_room.rl_update()
            if "get_invitation" in datarecv:
                self.waiting_chat_room.chat_room_invite_sig.emit(
                    datarecv.split('get_invitation: ')[1])

    def run_oto(self):
        self.at_oto = True
        while self.at_oto:
            datarecv = receive(self.sock)
            if "oo_msg" in datarecv:
                msg = datarecv.split('oo_msg: ')[1]
                self.oto.msg_sig.emit(msg)
            if "oo_fin" in datarecv:
                if self.at_oto == True:
                    self.at_oto = False
                    self.oto.stop_sig.emit("FIN")

    def run_chat_room(self):
        self.at_chat_room = True
        while self.at_chat_room:
            datarecv = receive(self.sock)
            # print(datarecv)
            if "new_mem" in datarecv:
                self.chat_room.member.append(datarecv.split('new_mem: ')[1])
                self.chat_room.update_members()
            if "mem_leave" in datarecv:
                self.chat_room.member.remove(datarecv.split('mem_leave: ')[1])
                self.chat_room.update_members()
                if len(self.chat_room.member) == 0:
                    self.update_chatroom(self.chat_room)

            if "msg_group" in datarecv:
                msg = datarecv.split('msg_group: ')[1]
                self.chat_room.msg_sig.emit(msg)
            if "quit_confirm" in datarecv:
                self.at_chat_room = False
            if "invitee_list" in datarecv:
                self.chat_room.invite_sig.emit(datarecv)


class Connect(QWidget):

    def __init__(self):
        super().__init__()
        self.ip_line = QLineEdit(self)
        self.port_line = QLineEdit(self)
        self.name_line = QLineEdit(self)
        self.cancel_btn = QPushButton('cancel', self)
        self.connect_btn = QPushButton('connect', self)
        self.initUI()

    def initUI(self):
        ip_label = QLabel('IP Address', self)
        ip_label.move(20, 20)
        port_label = QLabel('Port', self)
        port_label.move(20, 50)
        name_label = QLabel('Nickname', self)
        name_label.move(20, 120)
        self.ip_line.move(80, 20)
        self.port_line.move(80, 50)
        self.name_line.move(80, 120)
        self.cancel_btn.move(220, 150)
        self.cancel_btn.resize(self.cancel_btn.sizeHint())
        self.cancel_btn.clicked.connect(QCoreApplication.instance().quit)
        self.connect_btn.clicked.connect(self.connect)
        self.connect_btn.move(140, 150)
        self.connect_btn.resize(self.connect_btn.sizeHint())
        self.setWindowTitle('Connect to server')
        self.resize(300, 200)
        self.show()

    def checkInput(self, name, port, ip_address):
        if (" " or ":" or ";" or "(" or ")" or "[" or "]" or "\"" or "\'") in name:
            return True

        try:
            # Convert it into integer
            val = int(port)
            return False
        except ValueError:
            try:
                # Convert it into float
                val = float(port)
                return True
            except ValueError:
                return True

    def connect(self):
        ip_address = self.ip_line.text()
        port = self.port_line.text()
        name = self.name_line.text()
        if self.checkInput(name, port, ip_address):
            QMessageBox.warning(self, "Warning", "Invliad input, please try again.")
        else:
            client = Client(name)
            new = WaitingRoom(client)
            client.set_waiting_chat_room(new)
            self.close()
            new.show()


class WaitingRoom(QWidget):
    oto_sig = pyqtSignal(str)
    oto_refuse_sig = pyqtSignal()
    chat_room_created_sig = pyqtSignal()
    chat_room_joined_sig = pyqtSignal(str)
    chat_room_invite_sig = pyqtSignal(str)

    def __init__(self, client):
        super().__init__()
        self.close_button = QPushButton('Close')
        self.create_chat_room_button = QPushButton('Create')
        self.join_chat_room_button = QPushButton('Close')
        self.chat_room_list = QListWidget()
        self.one_to_oo_button = QPushButton('1 to 1 Chat')
        self.client_list = QListWidget()
        self.client = client
        threading.Thread(target=self.client.run_waiting_chat_room, args=()).start()
        self.initUI()

    def update_client_list(self):
        self.client_list.clear()
        i = 0
        for item in self.client.mem_list:
            i += 1
            if str(item) == str(self.client.name):
                self.client_list.insertItem(
                    i, QListWidgetItem(str(item) + " (You)"))
            else:
                self.client_list.insertItem(i, QListWidgetItem(str(item)))

    def rl_update(self):
        self.chat_room_list.clear()
        i = 0
        for i in range(len(self.client.chat_room_list)):
            i += 1
            self.chat_room_list.insertItem(
                i, QListWidgetItem("Room " + str(i) + " by " + str(self.client.chat_room_list[i - 1])))

    @QtCore.pyqtSlot(str)
    def receive_invite(self, target):
        reply = QMessageBox.question(
            self, 'Invitation', "You have been invite to Room by " + target + ". Do you want to accept?",
                                QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            send(self.client.sock, 'join_chat_room: ' +
                 target)

    @QtCore.pyqtSlot(str)
    def accept_oto(self, target):
        self.oto = OnetooneChat(self.client, target)

        self.oto.show()

    @QtCore.pyqtSlot()
    def chat_room_created(self):
        self.chat_room = ChatRoom(
            self.client, self.client.name, [self.client.name])

        self.chat_room.show()
        self.chat_room.update_members()

    @QtCore.pyqtSlot()
    def oto_rejected(self):
        QMessageBox.warning(self, "Warning", "Chat Refused.")

    @QtCore.pyqtSlot(str)
    def chat_room_joined(self, chat_room):
        name = chat_room.split(";")[0]
        members = list(chat_room.split(";")[1].replace("chat_room_member: ", "").replace(
            "\'", "").replace(",", "").replace("[", "").replace("]", "").replace("(", "").replace(")", "").replace(";",
                                                                                                                   "").lstrip().split(
            " "))
        self.chat_room = ChatRoom(
            self.client, name, members)

        self.chat_room.show()
        self.chat_room.update_members()

    def start_oto(self):
        if len(self.client_list.selectedIndexes()) == 0:
            QMessageBox.warning(self, "Warning", "You haven't selected anyone yet.")
        elif "You" not in str(self.client_list.selectedIndexes()[0].text()):
            send(self.client.sock, 'oo_request: ' + self.client.name + "::" +
                 str(self.client_list.selectedIndexes()[0].text()))

        else:
            QMessageBox.warning(self, "Warning", "You cannot select yourself.")
    def close_up(self):
        self.close()
       
    def send_create(self):
        send(self.client.sock, 'create_chat_room')

    def join_chat_room(self):
        if len(self.chat_room_list.selectedIndexes()) == 0:
            QMessageBox.warning(self, "Warning", "You haven't selected anything yet.")
        else:
            send(self.client.sock, 'join_chat_room: ' +
                 str(self.chat_room_list.selectedIndexes()[0].text()))

    def initUI(self):
        self.chat_room_created_sig.connect(self.chat_room_created)
        self.chat_room_joined_sig.connect(self.chat_room_joined)
        self.oto_sig.connect(self.accept_oto)
        self.oto_refuse_sig.connect(self.oto_rejected)
        self.chat_room_invite_sig.connect(self.receive_invite)
        self.update_client_list()
        self.one_to_oo_button.clicked.connect(self.start_oto)
        vb_oo_button = QVBoxLayout()
        vb_oo_button.addWidget(self.one_to_oo_button)
        vb_oo_button.setAlignment(Qt.AlignTop)
        hb_oto = QHBoxLayout()
        hb_oto.addWidget(self.client_list)
        hb_oto.addLayout(vb_oo_button)
        self.create_chat_room_button.clicked.connect(self.send_create)
        self.join_chat_room_button = QPushButton('Join')
        self.join_chat_room_button.clicked.connect(self.join_chat_room)
        vb_chat_room = QVBoxLayout()
        vb_chat_room.addWidget(self.create_chat_room_button)
        vb_chat_room.addWidget(self.join_chat_room_button)
        self.close_button.clicked.connect(self.close_up)
        vb_chat_room.addWidget(self.close_button)
        vb_chat_room.setAlignment(Qt.AlignTop)
        hb_chat_room = QHBoxLayout()
        hb_chat_room.addWidget(self.chat_room_list)
        hb_chat_room.addLayout(vb_chat_room)
        hb_close = QHBoxLayout()
        hb_close.addWidget(self.join_chat_room_button)
        vb = QVBoxLayout()
        vb.addWidget(QLabel('Connected Clients List'))
        vb.addLayout(hb_oto)
        vb.addWidget(QLabel('Chat Rooms'))
        vb.addLayout(hb_chat_room)
        vb.addLayout(hb_close)
        self.setLayout(vb)
        self.setWindowTitle('Waiting Room ' + self.client.name)
        self.setGeometry(350, 400, 350, 400)
        self.show()
        self.rl_update()


class OnetooneChat(QWidget):
    stop_sig = pyqtSignal(str)
    msg_sig = pyqtSignal(str)

    def __init__(self, client, target):
        super().__init__()
        self.close_button = QPushButton('Close')
        self.tb = QTextBrowser()
        self.send_button = QPushButton('Send')
        self.send_line = QLineEdit()
        self.client = client
        self.target = target
        self.client.set_oto(self)
        self.initUI()
        threading.Thread(target=self.client.run_oto, args=()).start()

    @QtCore.pyqtSlot(str)
    def msg_in(self, msg):
        self.tb.append(msg)

    @QtCore.pyqtSlot(str)
    def oto_quit(self, msg):
        # quit by other clients
        self.close()
        new = WaitingRoom(self.client)
        self.client.set_waiting_chat_room(new)
        new.show()
        new.update_client_list()

    def send_msg(self):
        if self.send_line.text():
            timel = time.strftime("%H:%M", time.localtime())
            msg = "Me (" + timel + "): " + self.send_line.text()
            self.tb.append(msg)
            self.send_line.clear()
            send(self.client.sock, 'oo_msg: ' + msg)

    def end_oto(self):
        # quit by this client
        send(self.client.sock, 'oo_fin')
        self.close()
        self.client.at_oto = False
        new = WaitingRoom(self.client)
        self.client.set_waiting_chat_room(new)
        new.show()

    def initUI(self):
        self.msg_sig.connect(self.msg_in)
        self.stop_sig.connect(self.oto_quit)
        self.tb.setAcceptRichText(True)
        self.tb.setOpenExternalLinks(True)
        self.send_button.clicked.connect(self.send_msg)
        hb_send = QHBoxLayout()
        hb_send.addWidget(self.send_line)
        hb_send.addWidget(self.send_button)
        self.close_button.clicked.connect(self.end_oto)
        vb = QVBoxLayout()
        vb.addWidget(QLabel('Chat with ' + self.target))
        vb.addWidget(self.tb)
        vb.addLayout(hb_send)
        vb.addWidget(self.close_button)
        self.setLayout(vb)
        self.setWindowTitle('1 to 1 Chat')
        self.setGeometry(350, 400, 350, 350)
        self.show()


class ChatRoom(QWidget):
    msg_sig = pyqtSignal(str)
    invite_sig = pyqtSignal(str)

    def __init__(self, client, chat_room_name, member):
        super().__init__()
        self.inv_button = QPushButton('Invite')
        self.tb_members = QListWidget()
        self.close_button = QPushButton('Close')
        self.send_button = QPushButton('Send')
        self.tb = QTextBrowser()
        self.send_line = QLineEdit()
        self.client = client
        self.chat_room_name = chat_room_name
        self.member = member
        self.client.set_chat_room(self)
        threading.Thread(target=self.client.run_chat_room, args=()).start()
        self.initUI()

    @QtCore.pyqtSlot(str)
    def msg_in(self, msg):
        self.tb.append(msg)

    def update_members(self):
        self.tb_members.clear()
        for m in self.member:
            i = 0
            if self.chat_room_name == m:
                m = m + " (Host)"
            elif self.client.name == m:
                m = m + " (You)"
            self.tb_members.insertItem(
                i, QListWidgetItem(m))

    def send_msg(self):
        if self.send_line.text():
            timel = time.strftime("%H:%M", time.localtime())
            msg = "Me (" + timel + "): " + self.send_line.text()
            self.tb.append(msg)
            self.send_line.clear()
            send(self.client.sock, 'msg_group: ' + msg)

    def leave_chat_room(self):
        send(self.client.sock, 'quit_chat_room')
        self.close()
        new = WaitingRoom(self.client)
        self.client.set_waiting_chat_room(new)
        new.show()

    def invite(self):
        send(self.client.sock, 'inv_request')

    @QtCore.pyqtSlot(str)
    def begin_invite(self, datarecv):
        inv_list = list(datarecv.replace("invitee_list: ", "").replace(
            "\'", "").replace(",", "").replace("(", "").replace(")", "").split(" "))
        self.invite_window = Invite(
            self.client, inv_list, self.client.name, self.chat_room_name, self.member)
        self.invite_window.show()

    def initUI(self):
        self.msg_sig.connect(self.msg_in)
        self.invite_sig.connect(self.begin_invite)
        self.tb.setAcceptRichText(True)
        self.tb.setOpenExternalLinks(True)
        self.send_button.clicked.connect(self.send_msg)
        hb_send = QHBoxLayout()
        hb_send.addWidget(self.send_line)
        hb_send.addWidget(self.send_button)
        self.close_button.clicked.connect(self.leave_chat_room)
        vb = QVBoxLayout()
        vb.addWidget(QLabel('Room By ' + self.chat_room_name))
        vb.addWidget(self.tb)
        vb.addLayout(hb_send)
        vb.addWidget(self.close_button)
        self.tb_members.resize(10, 10)
        self.inv_button.clicked.connect(self.invite)
        vb_members = QVBoxLayout()
        vb_members.addWidget(QLabel('Members'))
        vb_members.addWidget(self.tb_members)
        vb_members.addWidget(self.inv_button)
        vb_member_widget = QWidget()
        vb_member_widget.setLayout(vb_members)
        vb_member_widget.setFixedWidth(110)
        hb_all = QHBoxLayout()
        hb_all.addLayout(vb)
        hb_all.addWidget(vb_member_widget)
        self.setLayout(hb_all)
        self.setWindowTitle('Chat room')
        self.setGeometry(350, 400, 450, 300)
        self.show()


class Invite(QWidget):

    def __init__(self, client, inv_list, myself, chat_room, current_member):
        super().__init__()
        self.inv_list_widget = QListWidget()
        self.inv_button = QPushButton('Invite')
        self.cancel_button = QPushButton('Cancel')
        self.client = client
        self.inv_list = inv_list
        self.myself = myself
        self.chat_room = chat_room
        self.current_member = current_member
        self.initUI()

    def close_myself(self):
        self.close()

    def send_to_invitee(self):
        if len(self.inv_list_widget.selectedIndexes()) == 0:
            QMessageBox.warning(self, "Warning", "You haven't selected anyone to invite.")
        else:
            send(self.client.sock, 'invitation: ' +
                 str(self.inv_list_widget.selectedIndexes()[0].text()) + "::" + self.chat_room)
        self.close()

    def initUI(self):

        i = 0
        for i in range(len(self.inv_list)):
            invitee = self.inv_list[i]
            if invitee != self.myself and invitee not in self.current_member:
                self.inv_list_widget.insertItem(
                    i, QListWidgetItem(str(invitee)))
                i += 1

        self.inv_button.clicked.connect(self.send_to_invitee)
        self.cancel_button.clicked.connect(self.close_myself)
        hb = QHBoxLayout()
        hb.addWidget(self.inv_button)
        hb.addWidget(self.cancel_button)
        vb = QVBoxLayout()
        vb.addWidget(QLabel('Connected Clients'))
        vb.addWidget(self.inv_list_widget)
        vb.addLayout(hb)
        self.setLayout(vb)
        self.setWindowTitle('Connected Clients')
        self.setGeometry(350, 400, 200, 300)
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Connect()
    sys.exit(app.exec_())
