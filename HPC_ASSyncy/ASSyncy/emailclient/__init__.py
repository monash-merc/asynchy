from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from jinja2 import Environment, FileSystemLoader
import logging


class EmailClient:
    def __init__(self, config):
        # setup logging
        logging_dict = {
            "logging.ERROR": logging.ERROR,
            "logging.WARNING": logging.WARNING,
            "logging.INFO": logging.INFO,
            "logging.DEBUG": logging.DEBUG,
        }

        self.logger = logging.getLogger("email")
        self.logger.setLevel(logging_dict[config["log-level"]])

        # fh = logging.FileHandler(config["log-files"]["email"])
        fh = logging.handlers.RotatingFileHandler(config["log-files"]["email"], maxBytes=1 * 1024 * 1024, backupCount=5)
        fh.setLevel(logging_dict[config["log-level"]])
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s:%(process)s: %(message)s"
        )
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

        self.template_source_folder = config["epnalert-template-folder"]
        self.template_text = config["epnalert-template-text"]
        self.template_html = config["epnalert-template-html"]
        self.email_from = config["epnalert-email-from"]
        self.email_to = config["epnalert-email-to"]
        self.smtp = config["epnalert-email-smtp"]

    def send(self, msg_vars, debug=True):
        """If debug is set to true, don't actually send the email"""
        # prepare environment to read Jinja templates
        env = Environment(loader=FileSystemLoader(self.template_source_folder))
        # obtain the text and html template
        template_text = env.get_template(self.template_text)
        template_html = env.get_template(self.template_html)

        # create the Mulitpart email
        this_msg = MIMEMultipart("alternative")
        this_msg["Subject"] = "Unknown ownership of EPNs"
        this_msg["From"] = self.email_from
        this_msg["To"] = self.email_to

        # render the text and html parts using Jinja
        text = template_text.render(**msg_vars)
        html = template_html.render(**msg_vars)

        self.logger.debug("Text: {}".format(text))
        self.logger.debug("HTML: {}".format(html))

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")

        # attach the text and html parts to the email
        this_msg.attach(part1)
        this_msg.attach(part2)

        self.logger.info(
            "Sending notification to: {} from: {}".format(
                this_msg["to"], this_msg["from"]
            )
        )
        if not debug:
            s = smtplib.SMTP(self.smtp)
            response = s.send_message(this_msg)
            s.quit()
            self.logger.debug("SMTP response: {}".format(str(response)))
