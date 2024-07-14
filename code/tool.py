# -*- coding: utf-8 -*-
# @Time    : 2024/6/16
# @Author  : Blue
import csv
import os
import random
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from DrissionPage import ChromiumOptions, WebPage
from loguru import logger
from retrying import retry


class Tool:
    def __init__(self):
        self.s = requests.session()

        co = ChromiumOptions(read_file=False)
        base_path = Path(sys.argv[0]).parent
        co.set_browser_path(base_path.joinpath('Chrome', 'APP', 'Chrome.exe'))
        co.mute(True)
        co.auto_port(True)
        self.page = WebPage(chromium_options=co, session_or_options=False, timeout=60)
        self.page.listen.start('https://us.shein.com/api/productList/info/get', )  # 开始监听，指定获取包含该文本的数据包
        self.page.get('https://us.shein.com')
        print('等待触发...')
        packet = self.page.listen.wait(count=1)
        self.s.headers = packet.request.headers
        for cookie in self.page.cookies():
            self.s.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
        # 解析URL
        parsed_url = urlparse(packet.request.url)

        # 获取查询参数
        query_params = parse_qs(parsed_url.query)
        self.params = {k: v if len(v) > 1 else v[0] for k, v in query_params.items()}
        print(self.params)
        self.page.quit()

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def get_detail(self, goods_id):
        params = (
            ('_ver', '1.1.8'),
            ('_lang', 'en'),
            ('goods_id', goods_id),
            ('template', '1'),
            ('mallCode', '1'),
            ('isFromDetail', '1'),
            ('specialSceneType', '0'),
        )

        response = self.s.get('https://us.shein.com/api/productInfo/quickView/get', params=params)
        result = response.json()
        goods = result['info']['goods']
        return goods

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def get_list(self, start, end):
        for page in range(start, end + 1):
            print(f'页数: {page}')
            self.params['page'] = str(page)
            response = self.s.get('https://us.shein.com/api/productList/info/get', params=self.params)
            result = response.json()
            if not result['goods']:
                break

            for item in result['goods']:
                goods_id = item['goods_id']
                goods_url_name = item['goods_url_name']
                url = f'https://us.shein.com/{goods_url_name.replace(" ", "-")}-p-{goods_id}.html'
                print(f'商品URL: {url}')
                yield f'{goods_url_name.replace(" ", "-")}-p-{goods_id}', goods_id
                time.sleep(random.uniform(1, 3))
            time.sleep(random.uniform(1, 3))

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def download(self, url, file_path):
        img_url = url if (url.startswith('http') or url.startswith('https')) else 'https:' + url
        print(f'下载图片: {img_url}')
        response = requests.get(img_url, stream=True, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'})

        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

    def run(self, start, end):
        print('开始运行...')
        for goods_name, goods_id in self.get_list(start, end):
            save_path = Path(sys.argv[0]).parent.joinpath('结果', str(goods_id))
            save_path.mkdir(exist_ok=True, parents=True)
            img_path = save_path.joinpath('图片')
            img_path.mkdir(exist_ok=True, parents=True)

            goods = self.get_detail(goods_id)
            with open(save_path.joinpath('数据.csv'), 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                title = goods['detail']['goods_name']
                price = goods['getPrice']['salePrice']['amountWithSymbol']

                writer.writerow(['标题: ', title])
                writer.writerow(['价格: ', price])

                writer.writerow([])
                writer.writerow([])

                color = []
                for item in goods['colorData']['colorList']:
                    color.append(item['goods_title'])
                writer.writerow(['颜色: '] + color)

                writer.writerow([])
                writer.writerow([])

                des = {}
                for item in goods['detail']['productDetails']:
                    attr_name = item['attr_name']
                    attr_value = item['attr_value']
                    if des.get(attr_name):
                        des[attr_name] += ',' + attr_value
                    else:
                        des[attr_name] = attr_value

                for item in des.items():
                    writer.writerow(item)

                writer.writerow([])
                writer.writerow([])

                attr = []
                for item in sorted(goods['sizeInfoDes']['dimensionAttrInfo'],
                                   key=lambda x: x['sort']):
                    attr.append(item['attr_name'])

                us = {}
                for item in goods['localSizeList']['size_rule_list']:
                    us[item['name']] = item['correspond']
                if us:
                    writer.writerow(['SIZE', 'US'] + attr)
                else:
                    writer.writerow(['SIZE'] + attr)

                for item in goods['sizeInfoDes']['sizeInfo']:
                    attr_value_name = item['attr_value_name']
                    if us:
                        l = [attr_value_name, us[attr_value_name]]
                    else:
                        l = [attr_value_name]

                    for attr_value in attr:
                        l.append(item[attr_value])
                    writer.writerow(l)

                print('写入表格完毕!')
                print('开始下载图片...')
                for index, item in enumerate(goods['goods_imgs']['detail_image']):
                    self.download(item.get('origin_image_url') or item['origin_image'],
                                  img_path.joinpath(f'{index}.jpg'))
                print('下载完毕!')
        print('运行完毕！')


if __name__ == '__main__':
    try:

        os.system('chcp 65001')
        start, end = input('输入页数区间 例(1-5):').split('-')
        print(f'采集 {start}-{end}页...')
        t = Tool()
        t.run(int(start), int(end))
    except:
        logger.error('出现错误!')
        logger.error(traceback.format_exc())
    finally:
        os.system('pause')
