import logging
import pickle
import zlib
from hashlib import sha1

import pymongo
from enum import Enum, unique
# from queue import Queue # queue：FIFO先进先出后进后出的结构，有lock，多个线程执行时不会存在安全性问题，这里没使用是因为队列存在数据库中，可以多机、间断执行
from random import random
from threading import Thread, current_thread, local
from time import sleep
from urllib.parse import urlparse

import redis
import requests
from bs4 import BeautifulSoup
from bson import Binary # 不要单独安装，在安装pymongo时会自动安装


class Constans(object):
    """定义一个常量类"""
    urser_agent = 'Mozilla/5.0 (Android; Mobile; rv:14.0) Gecko/14.0 Firefox/14.0'
    proxies = {
        "http": "http://111.183.231.117:61234/",
    }


@unique # 表示内容具有唯一性
class SpiderStatus(Enum):
    """定义一个枚举类"""
    IDLE = 0
    WORKING = 1


def any_thread_alive(spider_threads):
    """判断在所有线程中是否存在还处于工作状态的线程"""
    # any(),all()全局函数，any()只要有一个为真则返回真，all()只有全部为真才返回真
    return any([spider_thread.spider.status == SpiderStatus.WORKING for spider_thread in spider_threads])


def decode_html_page(page, charsets):
    """页面解码"""
    page_html = None
    for charset in charsets:
        try:
            page_html = page.content.decode(charset)
            break # 只要解析出页面则跳出循环
        except Exception as e:
            logging.error(e) # 如果在给定编码解析失败则打印错误日志
    return page_html


class Retry(object):
    """用类定义的一个装饰器，可以定义执行次数及每次执行间等待的时间"""
    def __init__(self, *, retry_times=3, wait_secs=5, errors=(Exception,)):
        self.retry_time = retry_times
        self.wait_secs = wait_secs
        self.errors = errors

    def __call__(self, func):
        """魔法方法：自定义装饰器必须写在这个方法下"""
        def wapper(*args, **kwargs):
            for _ in range(self.retry_time):
                try:
                    return func(*args, **kwargs)
                except self.errors as e:
                    logging.error(e) # 如果在给定次数执行失败，则打印错误信息
                    sleep(int(self.wait_secs) * (random() + 1))
            return None
        return wapper


class Spider(object):
    """配置爬虫属性和方法"""
    def __init__(self):
        """定义默认工作状态"""
        self.status = SpiderStatus.IDLE

    @Retry() # 自定义装饰器调用方法，要加（）括号。
    def fetch(self, current_url, *, user_agent=None, proxies=None, charsets=('gb2312', 'utf-8', 'gbk')):
        """获取页面"""
        Tread_name = current_thread().name
        print(f'{Tread_name}：{current_url}')
        headers = {'user-agent': user_agent} if user_agent else {}
        page = requests.get(current_url, headers=headers, proxies=proxies)
        return decode_html_page(page, charsets) if page.status_code == 200 else None

    def parse(self, html_page, domain='www.geyanw.com'):
        """解析页面中url"""
        if html_page:
            soup = BeautifulSoup(html_page, 'lxml') # lxml引擎比自带的快速，性能更好
            for a_tag in soup.select_one('div[id="p_left"]').select('a[href]'):
                # 对残缺url进行补充
                parser = urlparse(a_tag.attrs['href'])
                scheme = parser.scheme or 'https'                      # 获取协议
                netloc = parser.netloc or domain                        # 获取域名
                if netloc == domain and scheme != 'javascript':
                    path = parser.path                                  # 获取相对路径
                    query = '?' + parser.query if parser.query else '' # 获取传递的参数
                    full_url = f'{scheme}://{netloc}{path}{query}'    # 新版python格式化字符串写法
                    redis_client = thread_local.redis_client
                    if not redis_client.sismember('visited_url', full_url): # redis数据库操作
                        redis_client.rpush('task_list', full_url)
                        print('full_url:' + full_url)

    def extract(self, html_page):
        """获取标题和类容"""
        if html_page:
            soup = BeautifulSoup(html_page, 'lxml')
            title = content = ''
            try:
                title = soup.select_one('div[id="p_left"]').select_one('div[class="title"]').find('h2').text
            except Exception as e:
                pass

            try:
                content_ps = soup.select_one('div[id="p_left"]').select_one('div[class="content"]').find_all('p')
                for content_p in content_ps:
                    content += content_p.text
            except Exception as e:
                pass

            return title, content

    def store(self, my_dict):
        mongo_db = thread_local.mongo_db
        hasher = hash_proto.copy()  # 应用已经创建好的摘要函数，不要每次循环都自己创建
        hasher.update(my_dict['content'].encode('utf-8'))
        doc_id = hasher.hexdigest()
        mongo_data_coll = mongo_db[my_dict['current_path']]  # 动态创建mongodb集合
        if not mongo_data_coll.find_one({'_id': doc_id}):  # 把内容摘要作为_id，防止url不一样，内容一样的存入数据库
            mongo_data_coll.insert_one(
                dict(_id=doc_id, path=my_dict['current_path'], url=my_dict['current_url'], title=my_dict['title'],
                        content=Binary(zlib.compress(pickle.dumps(my_dict['content'])))))
            print('存入mongodb成功')


class SpiderThread(Thread):
    """配置线程"""
    def __init__(self, name, spider):
        """定义线程名字和参数"""
        super().__init__(name=name, daemon=True) # 守护线程：daemon = True
        self.spider = spider

    def run(self):
        """线程方法，必须写在run()方法里面"""
        redis_client = redis.Redis(host='localhost', port=6379)  # 连接mongodb,并创建数据库
        mongo_client = pymongo.MongoClient(host='localhost', port=27017)  # 注意，这里不要把连接数据库函数放入__init__中，否则会产生循环引用（软连接）
        thread_local.redis_client = redis_client
        thread_local.mongo_db = mongo_client.geyanwang
        while True:
            current_url = redis_client.lpop('task_list')
            while not current_url:
                self.spider.status = SpiderStatus.IDLE
                current_url = redis_client.lpop('task_list')
            if current_url:
                self.spider.status = SpiderStatus.WORKING  # 改变爬虫工作状态
                current_url = current_url.decode('utf-8') # 由于url存在redis数据库，所以取出来时不时str,需要自行解码
            if not redis_client.sismember('visited_url', current_url):
                redis_client.sadd('visited_url', current_url)

                html_page = self.spider.fetch(current_url, user_agent=Constans.urser_agent, proxies=Constans.proxies)
                if html_page:
                    title, content = self.spider.extract(html_page)
                    current_path = '' # 取分类的字段
                    try:
                        current_path = urlparse(current_url).path.split('/')[1]
                    except Exception as e:
                        pass
                    if current_path and title and content:
                        my_dict = dict(current_url=current_url,current_path=current_path,title=title,content=content)
                        self.spider.store(my_dict)
                    self.spider.parse(html_page)


thread_local = local()  # ThreadLocal 是线程的局部变量， 是每一个线程所单独持有的，其他线程不能对其进行访问
hash_proto = sha1()  # 创建好摘要函数，要用时直接copy一份，不要再去创建，提升程序性能 # hasher = hash_proto.copy()


def main():
    redis_client = redis.Redis(host='localhost', port=6379)  # 连接redis
    if not redis_client.exists('task_list'):
        redis_client.rpush('task_list', 'https://www.geyanw.com/')  # 添加根url
    spider_threads = [SpiderThread('th-%d' % i, Spider()) for i in range(10)]
    for spider_thread in spider_threads: # 创建10个线程，并启动
        spider_thread.start()
    # 检查url是否执行完，并且检查是否所有线程都停止工作，否则，将在这里自循环，不往下执行
    # redis中的有序列表，如果里面没有值，则自动删除列表
    while redis_client.exists('task_list') or any_thread_alive(spider_threads):
        pass
    print('Over!')


if __name__ == '__main__':
    main()
