# encoding=utf-8
import ast
import traceback
import re
import json
import sys
import time
import traceback
import requests

from login import Login
from send_mail import send_mail

# from requests_toolbelt.utils import dump

try_times = 3  # 失败这么多次后就直接不管了
delay = 2  # 访问页面前的延迟，为了防止过快访问网站被封IP

# headers，所有的请求都用这个作为headers
headers = {
    'Host': 'm.nuaa.edu.cn',
    'Connection': 'close',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Sec-Fetch-Dest': 'empty',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 10; TAS-AN00 Build/HUAWEITAS-AN00)',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': 'https://m.nuaa.edu.cn',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Referer': 'https://m.nuaa.edu.cn/uc/wap/login/check',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cookie': ''
}


# 登陆并且返回json形式的cookie，如果登陆失败返回空串
# 先访问/uc/wap/login，获得eai-sess，然后带着她访问/uc/wap/login/check，获得UUkey
def login(stu_number, password):
    cookies = ''
    for _ in range(try_times):
        try:
            time.sleep(delay)
            response = requests.get(
                'http://m.nuaa.edu.cn/uc/wap/login', cookies=cookies)
            print('get login page:', response.status_code)

            # cookies = response.headers['Set-Cookie']
            # cookies = re.search(r'eai-sess=([a-zA-Z0-9]+)', cookies).group(0)
            cookies = dict(response.cookies)

            time.sleep(delay)
            response = requests.get('http://m.nuaa.edu.cn/uc/wap/login/check', cookies=cookies,
                                    data='username={}&password={}'.format(stu_number, password))
            print('login...:', response.status_code)

            # cookies2 = response.headers['Set-Cookie']
            # cookies = cookies + '; ' + \
            #     re.search(r'UUkey=([a-zA-Z0-9]+)', cookies2).group(0)
            cookies.update(dict(response.cookies))

            # print(cookies)
            print(response.text)
            return cookies, '登陆结果：' + response.text + '\n'
        except:
            print('login failed.')
            traceback.print_exc()
            pass
    # raise Exception('lOGIN FAIL')
    return {}, '登陆结果：login faild,请检查账号密码\n'


# 使用统一身份认证登陆
def new_login(login_id, login_password, stu_name, imei, mobiletype):
    '''
    登陆I南航，返回Cookie，失败返回空串
    '''
    cookie, message = Login(stu_name, login_id, login_password, imei, mobiletype).login()
    if cookie == -1:
        return "", message
    else:
        return cookie, message


# longitude: 经度； latitude: 纬度
# 根据经纬度访问高德API，并且返回打卡时候“geo_api_info”字段的值
def get_address_info(longitude, latitude):
    for _ in range(try_times):
        try:
            time.sleep(delay)
            response = requests.get(
                'http://restapi.amap.com/v3/geocode/regeo', params={
                    'key': '729923f88542d91590470f613adb27b5',
                    's': 'rsv3',
                    'location': str(longitude) + ',' + str(latitude)
                })
            geo_data = json.loads(response.text)
            geo_data = geo_data['regeocode']
            geo_api_info = {
                "type": "complete",
                "position": {
                    "Q": latitude,
                    "R": longitude,
                    "lng": longitude,
                    "lat": latitude
                },
                "location_type": "html5",
                "message": "Get ipLocation failed.Get geolocation success.Convert Success.Get address success.",
                "accuracy": 102,  # ???
                "isConverted": True,  # ?
                "status": 1,
                "addressComponent": {
                    "citycode": geo_data['addressComponent']['citycode'],
                    "adcode": geo_data['addressComponent']['adcode'],
                    "businessAreas": [],
                    "neighborhoodType": "",
                    "neighborhood": "",
                    "building": "",
                    "buildingType": "",
                    "street": geo_data['addressComponent']['streetNumber']['street'],
                    "streetNumber": geo_data['addressComponent']["streetNumber"]['number'],
                    "country": geo_data['addressComponent']['country'],
                    "province": geo_data['addressComponent']['province'],
                    "city": geo_data['addressComponent']['city'],
                    "district": geo_data['addressComponent']['district'],
                    "township": geo_data['addressComponent']['township']
                },
                "formattedAddress": geo_data['formatted_address'],
                "roads": [],
                "crosses": [],
                "pois": [],
                "info": "SUCCESS"
            }
            return geo_api_info
        except:
            traceback.print_exc()
    return geo_api_info
    # print(dump.dump_all(response).decode('utf-8'))


# 获取uid，id，打卡时候会用到，获取失败异常最可能的原因是账号密码错误
def get_uid_id(cookies):
    for _ in range(try_times):
        try:
            time.sleep(delay)
            # response = requests.get(
            #     'http://m.nuaa.edu.cn/ncov/wap/default', cookies=cookies)
            headers['Cookie'] = cookies
            response = requests.get(
                'http://m.nuaa.edu.cn/ncov/wap/default', headers=headers)
            response.encoding = 'utf-8'
            # '{"e":10013,"m":"用户信息已失效,请重新进入页面","d":{"login_url":"https://m.nuaa.edu.cn/uc/wap/login?redirect=https%3A%2F%2Fm.nuaa.edu.cn%2Fuc%2Fwap%2Flogin%2Fcheck"}}'
            if "操作成功" in response.text:
                uid = re.search(r'"uid":"([0-9]*)"', response.text).group(1)
                id = re.search(r'"id":([0-9]*)', response.text).group(1)
                return uid, id, "操作成功"
            else:
                return 0, 0, "获取id、uid失败，可能为cookie失效"
        except:
            traceback.print_exc()
    # 就这样吧，让他崩溃，万一假打卡了就不好了
    print('获取id、uid失败')
    return False, '获取id、uid失败\n'


# 签到，返回True成功，否则失败
def check(cookies, geo_api_info, id, uid):
    # Post的data，如果你是勇士可以尝试给这个打上注释，老谜语人了，看不懂ヾ(•ω•`)o
    data = {
        'sfzhux': '1',
        'zhuxdz': '',
        'szgj': '',
        'szcs': '',
        'szgjcs': '',
        'sfjwfh': '0',
        'sfyjsjwfh': '0',
        'sfjcjwfh': '0',
        'sflznjcjwfh': '0',
        'sflqjkm': '4',
        'jkmys': '0',
        'sfjtgfxdq': '0',
        'nuaaxgymjzqk': '1',
        'dyzjzsj': '',
        'bfhzjyq': '0',
        'hxyxjzap': '0',
        'yjzjsj': '',
        'sfjkyc': '0',
        'sftjlkjc': '',
        'lkjctlsj': '',
        'sfsylkjcss': '',
        'gjzsftjlkjc': '',
        'gjzlkjctlsj': '',
        'gjzsfsylkjcss': '',
        'ifhxjc': '',
        'hsjconetime': '',
        'hsjconeplace': '',
        'hsjconejg': '',
        'hsjctwotime': '',
        'hsjctwoplace': '',
        'hsjctwojg': '',
        'hsjcthreetime': '',
        'hsjcthreeplace': '',
        'hsjcthreejg': '',
        'hsjcfourtime': '',
        'hsjcfourplace': '',
        'hsjcfourjg': '',
        'ywchxjctime': '',
        'hsjclist': '{}',
        'njrddz': '南京航空航天大学将军路校区南区',
        'gzczxq': '2',
        'ifznqgfxljs': '',
        'iflsqgfxljs': '',
        'zrwjtw': '1',
        'jrzjtw': '1',
        'jrlvymjrq': '',
        'ifcyglq': '0',
        'wskmyy': '',
        'zhycjgdqifjn': '',
        'dqsfzgfxszqs': '0',
        'gqsfyzgfxljs': '0',
        'gqsfyqzfhryjc': '0',
        'sfyjwljqyhg': '0',
        'cjfxsfhs': '',
        'bzxyy': '',
        'bzxyydesc': '',
        'id': id,  # 打卡的ID，其实这个没影响的
        'uid': uid,  # UID
        'date': time.strftime("%Y%m%d", time.localtime()),  # 打卡年月日一共8位
        'tw': '2',
        'sfcxtz': '0',
        'sfyyjc': '0',
        'jcjgqr': '0',
        'jcjg': '',
        'sfjcbh': '0',
        'sfcxzysx': '0',
        'qksm': '',
        'remark': '',
        'address': geo_api_info['formattedAddress'],
        'area': geo_api_info['addressComponent']['province'] + ' ' + geo_api_info['addressComponent']['city'] + ' ' +
                geo_api_info['addressComponent']['district'],
        'province': geo_api_info['addressComponent']['province'],
        'city': geo_api_info['addressComponent']['city'],
        'geo_api_info': json.dumps(geo_api_info, separators=(',', ':')),
        'created': round(time.time()),  # 时间戳
        'sfzx': '1',
        'sfjcwhry': '0',
        'sfcyglq': '0',
        'gllx': '',
        'glksrq': '',
        'jcbhlx': '',
        'jcbhrq': '',
        'sftjwh': '0',
        'sftjhb': '0',
        'fxyy': '',
        'bztcyy': '',
        'fjsj': '0',
        'created_uid': '0',
        'sfjchbry': '0',
        'sfjcqz': '',
        'jcqzrq': '',
        'jcwhryfs': '',
        'jchbryfs': '',
        'xjzd': '',
        'sfsfbh': '0',
        'sfjcwzry': '0',
        'sftjwz': '0',
        'jhfjrq': '',
        'jhfjjtgj': '',
        'jhfjhbcc': '',
        'jhfjsftjwh': '0',
        'jhfjsftjhb': '0',
        'szsqsfybl': '0',
        'sfygtjzzfj': '0',
        'gtjzzfjsj': '',
        'sfsqhzjkk': '0',
        'sqhzjkkys': '',
        'is_fx_log': '0',
        'fxzrwjtw': '0',
        'fxjrcjtw': '0',
        'fxjrzjtw': '0',
        'fxsfzx': '0',
        'fxsfcyglq': '0',
        'fxsfcxtz': '0',
        'sfjzxg': '0',
        'skmcolor': '1',
        'skmimg': '',
        'ifjrglkjc': '',
        'gtjjsfhm': '',
        'gtjzsfhzl': '',
        'sffhddjjgc': '',
        'ifjgzgfxq': '',
        'jgzgfxrq': '',
        'jgzgfxdq': '',
        'jgzgfxxxdz': '',
        'newwchsjccs': '',
        'dsdecjcsj': '',
        'dsdechsjcjgtype': '',
        'dsdrchsjcdd': '',
        'dsdechsjcjg': '',
        'zhyccjcsj': '',
        'zhycchsjcjgtype': '',
        'zhycchsjcdd': '',
        'zhycchsjcjg': '',
        'hsjczm': '',
        'sfmrhs': '',
        'gtjzryxcsfyc': '1',
        'gtjzryxcsfycQt': '',
        'gwszdd': '',
        'sfyqjzgc': '',
        'jrsfqzys': '',
        'jrsfqzfy': '',
        'ismoved': '0'
    }
    for _ in range(try_times):
        try:
            time.sleep(delay)
            headers['Cookie'] = cookies
            response = requests.post('https://m.nuaa.edu.cn/ncov/wap/default/save',
                                     data=data, headers=headers)
            # response = requests.post('http://m.nuaa.edu.cn/ncov/wap/default/save', data=data, cookies=cookies)
            print('sign statue code:', response.status_code)
            # print('sign return:', response.text)
            response.encoding = 'utf-8'

            if response.text.find('成功') >= 0:
                print('打卡成功')
                return True, '打卡成功' + '\n'
            else:
                print('打卡失败')
        except:
            traceback.print_exc()
    return False, '打卡失败' + '\n'


def send_result(config, recever, result, messgae):
    mail_sender = config['mail_sender']
    smtp_password = config['smtp_password']
    smtp_host = config['smtp_host']
    if result == True:
        send_mail(mail_sender, smtp_password, smtp_host,
                  recever, messgae, '打卡成功', '主人', '打卡姬')
    else:
        send_mail(mail_sender, smtp_password, smtp_host,
                  recever, messgae, '打卡失败', '主人', '打卡姬')


def main():
    config = sys.stdin.read()
    config = json.loads(config)
    # config = []
    # with open("stu.json", 'r', encoding='UTF-8') as f:
    #     config = json.load(f)

    imei = config['imei']
    mobiletype = config['mobiletype']
    for student in config['students']:
        result = False  # 打卡结果，False表示没有打上
        stu_name = student['name']
        stu_number = student['stu_number']
        password = student['password']
        longitude = student['longitude']
        latitude = student['latitude']
        mail = student['mail']
        message = ''
        message1 = ''
        message2 = ''
        print('--------------------------------------')
        try:
            # cookies, message = login(stu_number, password)
            cookies = student['cookie']
            if cookies == '':
                cookies, message = new_login(stu_number, password, stu_name, imei, mobiletype)
                uid, id, message1 = get_uid_id(cookies)
            else:
                uid, id, message1 = get_uid_id(cookies)
                # 可能使cookies失效了，重新登录
                if message1 != "操作成功":
                    cookies, message = new_login(stu_number, password, stu_name, imei, mobiletype)
                    uid, id, message1 = get_uid_id(cookies)

            geo_api_info = get_address_info(longitude, latitude)
            result, message2 = check(cookies, geo_api_info, id, uid)
            message += message1 + message2
        except:
            print('发生错误，可能原因是打卡密码错误或者经纬度错误')
            message += '发生错误，可能原因是打卡密码错误或者经纬度错误'
        if mail != '':
            send_result(config, mail, result, message)


if __name__ == '__main__':
    main()
