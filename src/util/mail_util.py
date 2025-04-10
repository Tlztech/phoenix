import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from util import env_util


def send_csv_attachment(subject, content):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = env_util.get_env('MAIL_FROM')
    msg['To'] = env_util.get_env('MAIL_TO')
    msg['Cc'] = env_util.get_env('MAIL_CC')

    # 生成CSV文件
    part = MIMEApplication(b'\xef\xbb\xbf' + content, Name='output.csv')
    part.add_header('Content-Type', 'text/csv', charset='utf-8')
    part.add_header('Content-Disposition', 'attachment', filename='output.csv')
    msg.attach(part)

    # 发送邮件
    with smtplib.SMTP_SSL(env_util.get_env('SMTP'), env_util.get_env('SMTP_PORT')) as server:
        server.login(env_util.get_env('MAIL_SENDER'), env_util.get_env('MAIL_P'))
        server.send_message(msg)


def send_message(subject, content):
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = env_util.get_env('MAIL_FROM')
    msg['To'] = env_util.get_env('MAIL_TO')

    with smtplib.SMTP_SSL(env_util.get_env('SMTP'), env_util.get_env('SMTP_PORT')) as server:
        server.login(env_util.get_env('MAIL_SENDER'), env_util.get_env('MAIL_P'))
        server.send_message(msg)
