class EmailClient():

    def send(self, tmplsrc, msgvars, debug=True):
        """If debug is set to true, don't actually send the email"""
        import smtplib

        import logging
        logger=logging.getLogger()
        import jinja2
        results = []
        template = jinja2.Template(tmplsrc)
        for recipient in msgvars['to']:
            thismsg = msgvars.copy()
            thismsg['to'] = recipient
            thismsg['from'] = 'help@massive.org.au'
            rendered = template.render(**thismsg)
            results.append(rendered)
            logger.info("Sending notification to {}".format(recipient))
            if not debug:
                s = smtplib.SMTP('smtp.monash.edu')
                s.sendmail(thismsg['from'], thismsg['to'], rendered)
                print(rendered)
        return results
