from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.common.keys import Keys


def main():
    driver = webdriver.Chrome()
    driver.get('https://v.taobao.com/v/content/live?catetype=704&from=taonvlang')
    elem = driver.find_element_by_css_selector('input[placeholder="输入关键词搜索"]')
    elem.send_keys('美女') # 自动传入搜索内容
    elem.send_keys(Keys.ENTER) # 自动回车
    soup = BeautifulSoup(driver.page_source, 'lxml')
    for img_tag in soup.select('img[src]'):
        print(img_tag.attrs['src'])


if __name__ == '__main__':
    main()