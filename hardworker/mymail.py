# -*- coding: utf-8 -*-

import smtplib as smtp
from email.mime.multipart import MIMEMultipart
from email import Encoders
from email import MIMEBase
from email.mime.text import MIMEText
import socket


class Mail_Sender(object):
    """Класс, хранящий в себе информацию, необходимую для отправки e-mail При
    инициализации объекта, выполняется попытка подключения, для проверки
    корректности данных."""

    def __init__(self, server, mail, password, from_name, subject):
        self.server = server
        self.mail = mail
        self.password = password
        self.from_name = from_name
        self.subject = subject
        if self.check_connection():
            try:
                server = smtp.SMTP_SSL(self.server,timeout=2)
                server.ehlo()
                server.login(self.mail, self.password)
            except:
                raise Exception("Not valid server/mail/password")

    def send_message(self, dest_email, message_text, file=None):
        """Метод, который отправляет сообщение по заданному адресу, с заданным
        содержимым. Возможно добавить файл.

        :param dest_email: Адрес доставки сообщения
        :param message_text: Текст сообщения
        :param file: Путь к файлу
        :return:
        """
        msg = MIMEMultipart()
        msg['Subject'] = self.subject
        msg['From'] = self.from_name
        msg['To'] = ', '.join(dest_email)

        msg.attach(MIMEText(message_text))

        if file:
            part = MIMEBase.MIMEBase('application', 'octet-stream')
            part.set_payload(open(file, 'rb').read())
            Encoders.encode_base64(part)

            part.add_header('Content-Disposition',
                            'attachment; filename="{}"'.format(file))

            msg.attach(part)
        server = smtp.SMTP_SSL(self.server)
        server.ehlo()
        server.login(self.mail, self.password)
        server.sendmail(self.mail, dest_email, msg.as_string())

    def check_connection(self):
        try:
            host = socket.gethostbyname("www.yandex.ru")
            s = socket.create_connection((host, 80), timeout=2)
            return True
        except:
            pass
        return False


