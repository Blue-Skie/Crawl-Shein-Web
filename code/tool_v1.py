# -*- coding: utf-8 -*-
# @Time    : 2024/6/24
# @Author  : Blue
import csv
import json
import re
import sys
from pathlib import Path

import requests
from DrissionPage import ChromiumOptions, WebPage
from retrying import retry


class Tool:
    def __init__(self):
        co = ChromiumOptions(read_file=False)
        base_path = Path(sys.argv[0]).parent
        co.set_browser_path(base_path.joinpath('Chrome', 'APP', 'Chrome.exe'))
        co.mute(True)
        # co.auto_port(True)
        self.page = WebPage(chromium_options=co, session_or_options=False, timeout=60)

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

    def run(self):
        while True:
            input('####按下回车开始采集>>>>>>>')
            try:
                print('开始采集...')
                html = self.page.latest_tab.html
                data = re.search('window\.gbRawData = (\{.*?})\n', html).group(1)
                data = json.loads(data.strip())
                title = data['productIntroData']['detail']['goods_name']
                price = data['productIntroData']['getPrice']['salePrice']['amountWithSymbol']

                save_path = Path(sys.argv[0]).parent.joinpath('结果', title.replace(" ", "-"))
                save_path.mkdir(exist_ok=True, parents=True)
                img_path = save_path.joinpath('图片')
                img_path.mkdir(exist_ok=True, parents=True)
                with open(save_path.joinpath('数据.csv'), 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)

                    writer.writerow(['标题: ', title])
                    writer.writerow(['价格: ', price])

                    writer.writerow([])
                    writer.writerow([])

                    color = []
                    for item in data['productIntroData']['colorData']['colorList']:
                        color.append(item['goods_title'])
                    writer.writerow(['颜色: '] + color)

                    writer.writerow([])
                    writer.writerow([])

                    des = {}
                    for item in data['productIntroData']['detail']['productDetails']:
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
                    for item in sorted(data['productIntroData']['sizeInfoDes']['dimensionAttrInfo'],
                                       key=lambda x: x['sort']):
                        attr.append(item['attr_name'])

                    writer.writerow(['SIZE', 'US'] + attr)
                    us = {}
                    for item in data['productIntroData']['localSizeList']['size_rule_list']:
                        us[item['name']] = item['correspond']
                    for item in data['productIntroData']['sizeInfoDes']['sizeInfo']:
                        attr_value_name = item['attr_value_name']

                        l = [attr_value_name, us[attr_value_name]]
                        for attr_value in attr:
                            l.append(item[attr_value])
                        writer.writerow(l)


                    print('写入表格完毕!')
                    print('开始下载图片...')
                    for index, item in enumerate(data['productIntroData']['goods_imgs']['detail_image']):
                        self.download(item.get('origin_image_url') or item['origin_image'],
                                      img_path.joinpath(f'{index}.jpg'))
                    print('下载完毕!')
                    print('采集完成!')
            except:
                print('=============')
                print('采集出错!')
                print('=============')


if __name__ == '__main__':
    t = Tool()
    t.run()
