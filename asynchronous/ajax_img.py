# Selenium是一个用于Web应用程序测试的工具。
# Selenium测试直接运行在浏览器中，就像真正的用户在操作一样,需要想要浏览器的驱动包（并配置环境变量），
from selenium import webdriver
from bs4 import BeautifulSoup


def main():
    driver = webdriver.Chrome()
    driver.get('https://v.taobao.com/v/content/live?catetype=704')
    soup = BeautifulSoup(driver.page_source, 'lxml')
    for img_tag in soup.select('img[src]'):
        print(img_tag.attrs['src'])


if __name__ == '__main__':
    main()