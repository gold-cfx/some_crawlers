# 建立在requests和BeautifulSoup之上的爬虫工具
import robobrowser


def main():
    b = robobrowser.RoboBrowser(parser='lxml') # 传入解析方式
    b.open('https://github.com/login/')
    f = b.get_form(action='/session')
    f['login'].value = '644148993@qq.com'
    f['password'].value = 'your password'
    b.submit_form(f)
    for a_tag in b.select('a[href]'):
        print(a_tag.attrs['href'])


if __name__ == '__main__':
    main()