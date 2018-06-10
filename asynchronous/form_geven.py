import requests
from bs4 import BeautifulSoup


def main():
    resp = requests.get('https://github.com/login/')
    if resp.status_code != 200:
        return
    cookies = resp.cookies.get_dict()  # 获取cookie
    soup = BeautifulSoup(resp.text, 'lxml')
    utf8_value = soup.select_one('form input[name="utf8"]').attrs['value'] # 获取隐藏域内容
    authenticity_token_value = soup.select_one('form input[name="authenticity_token"]').attrs['value'] # 获取token
    data = {
        'utf8': utf8_value,
        'authenticity_token': authenticity_token_value,
        'login':'644148993@qq.com',
        'password': 'xxxxx'
    }
    resp = requests.post('https://github.com/session/', data=data, cookies=cookies) # 利用post请求提交
    print(resp.text)


if __name__ == '__main__':
    main()