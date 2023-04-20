import re
import configparser
import requests
from lxml import etree


class AWSAcademyLab:
    def __init__(self, config_file):
        self.get_config(config_file)
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
        }
        # update headers
        self.session.headers.update(self.headers)

    def get_config(self, config_file):
        '''
        load account and module url from config file
        '''
        config = configparser.ConfigParser()
        config.read(config_file)
        self.email = config['DEFAULT']['email']
        self.password = config['DEFAULT']['password']
        self.module_url = config['DEFAULT']['module_url']

    def login(self):
        '''
        login to awsacademy
        '''
        url = 'https://awsacademy.instructure.com/login/canvas'
        r = self.session.get(url)

        # extract form input name and value
        html = etree.HTML(r.text)
        params = {}
        for i in html.xpath('//form[@action="/login/canvas"]/input'):
            params[i.xpath('@name')[0]] = i.xpath('@value')[0]
        params['pseudonym_session[unique_id]'] = self.email
        params['pseudonym_session[password]'] = self.password
        params['pseudonym_session[remember_me]'] = '0'
        r = self.session.post(url, data=params)

    def load_module(self):
        '''
        load lab module to get vclab url and paylaod\\
        because the vclab cookie expires soon
        '''
        url = self.module_url
        r = self.session.get(url)

        # parse module html
        html = etree.HTML(r.text)
        form = html.xpath('//form')[0]
        # extract form action url
        vclab_url = form.xpath('@action')[0]
        # extract form input name and value
        payload = {}
        for i in form.xpath('//input'):
            name = i.xpath('@name')[0]
            value = i.xpath('@value')[0]
            payload[name] = value
        return (vclab_url, payload)

    def load_vclab(self, vclab_url, payload):
        '''
        load vclab and return startaws url
        '''
        r = self.session.post(vclab_url, data=payload)
        # redirect
        url = 'https://labs.vocareum.com/main/' + \
            re.search(r"location.href='(.*)';", r.text).group(1)
        r = self.session.get(url)

        # extract csrf token
        self.vockey = re.search(r"var csrfToken = \"(.*)\";", r.text).group(1)

        # concanate url
        url_prefix = 'https://labs.vocareum.com'
        url_path = re.search(r"(/util/vcput.php\?a=startaws.*)\"",
                             r.text).group(1) + '&vockey=' + self.vockey
        startaws_url = url_prefix+url_path

        return startaws_url

    def start_aws(self, url):
        r = self.session.get(url)
        if 'success' in r.text:
            print('start aws success!')

    def get_buget(self):
        '''
        get aws lab buget(experimental)
        '''
        url = 'https://labs.vocareum.com/util/vcput.php?a=getaws&type=1&stepid=1649052&version=0&v=3&vockey=' + self.vockey
        r = self.session.get(url)
        print('Baget Used:', r.json()[
              'total_spend'] + ' of ' + r.json()['total_budget'])

    def show_aws_act(self):
        '''
        save aws lab Cloud Access(experimental)
        '''
        url = 'https://labs.vocareum.com/util/vcput.php?a=getaws&type=1&stepid=1649052&version=0&v=0&vockey=' + self.vockey
        r = self.session.get(url)
        html = etree.HTML(r.text)
        aws_cli_conf = html.xpath('//div[@id="clikeybox"]/pre/span/text()')[0]
        with open('aws_credentials', 'w') as f:
            f.write(aws_cli_conf)
            print('aws cli credentials saved!')
        ssh_pkey = html.xpath('//div[@id="sshkeybox"]/pre/span/text()')[0]
        with open('ssh_pkey', 'w') as f:
            f.write(ssh_pkey)
            print('ssh private key saved!')

    def run(self):
        self.login()
        vclab_url, payload = self.load_module()
        startaws_url = self.load_vclab(vclab_url, payload)
        self.start_aws(startaws_url)

        try:
            self.get_buget()
            self.show_aws_act()
        except:
            print('Exprimental feature failed!')


if __name__ == '__main__':
    config_file = 'config.ini'
    app = AWSAcademyLab(config_file)
    app.run()
