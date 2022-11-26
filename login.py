import requests
import re
import js2py
import time
from urllib import parse

get_headers = {
    "Host": "authserver.nuaa.edu.cn",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

post_headers = {
    "Host": "authserver.nuaa.edu.cn",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Origin": "http://authserver.nuaa.edu.cn",
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Referer": "http://authserver.nuaa.edu.cn/authserver/login?service=http%3A%2F%2Fauthserver.nuaa.edu.cn%2Fauthserver%2Fmobile%2Fcallback%3FappId%3D779935806",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

mobile_headers = {
    "x-requested-with": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
    "Content-Length": "100",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; NTH-AN00 Build/HONORNTH-AN00)",
    "Host": "m.nuaa.edu.cn",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip"
}


class Login():

    def __init__(self, stu, username, password, imei, mobiletype='android',
                 url='http://authserver.nuaa.edu.cn/authserver/login?service=http%3A%2F%2Fauthserver.nuaa.edu.cn%2Fauthserver%2Fmobile%2Fcallback%3FappId%3D779935806',
                 jsFile='./password/encrypt.js', retry_limit=10):
        self.url = url
        self.stu = stu
        self.username = username
        self.password = password
        self.imei = imei
        self.mobiletype = mobiletype
        self.retry_limit = retry_limit
        self.sess = requests.Session()

        self.mobile_code = ""
        self.cookie = ""

        with open(jsFile, 'r', encoding='UTF-8') as file:
            jsCode = file.read()
        self.context = js2py.EvalJs()
        self.context.execute(jsCode)

    def getParam(self):
        r = self.sess.get(self.url, headers=get_headers)
        pattern1 = '<input type="hidden" id="pwdEncryptSalt" value="(.*?)" />'
        pattern2 = 'name="execution" value="(.*?)" />'
        html_data = r.text
        self.pwdEncryptSalt = re.findall(pattern1, html_data)[0]
        self.execution = re.findall(pattern2, html_data)[0]

    def getEncryptPWD(self):
        self.Enpassword = self.context.encryptPassword(self.password, self.pwdEncryptSalt)

    def getMobileCode(self):
        self.getParam()
        self.getEncryptPWD()
        data = 'username={}&password={}&captcha=&_eventId=submit&cllt=userNameLogin&dllt=generalLogin&lt=&execution={}'.format(
            self.username, parse.quote(self.Enpassword), parse.quote(self.execution))
        # time.sleep(2)
        r = self.sess.post(self.url, headers=post_headers, data=data)
        if 'mobile_code' in r.url:
            pos = r.url.find('=')
            self.mobile_code = r.url[pos + 1:]
            return True
        else:
            return False

    def getCookie(self):
        data = 'code={}&mobile_type={}&imei={}&sid={}'.format(self.mobile_code, self.mobiletype, self.imei, self.imei)
        r = requests.post('https://m.nuaa.edu.cn/a_nuaa/api/sso/login', headers=mobile_headers, data=data)
        if r.status_code == 200:
            try:
                cookies = r.headers['Set-Cookie']
                pos = cookies.find('; expires')
                self.cookie = cookies[:pos]
                return True
            except:
                return False
        else:
            return False

    def login(self):
        retry1 = 0
        retry2 = 0
        t = time.localtime()
        while self.getMobileCode() is False or self.mobile_code == "":
            if retry1 > self.retry_limit:
                print(self.stu, ' 统一身份认证失败')
                return -1, ' 统一身份认证失败\n'
            time.sleep(600)
            retry1 += 1

        while self.getCookie() is False or self.cookie == "":
            if retry2 > self.retry_limit:
                print(self.stu, " cookie获取失败")
                return -1, " cookie获取失败\n"
            time.sleep(600)
            retry2 += 1

        return self.cookie, "登陆成功\n"
