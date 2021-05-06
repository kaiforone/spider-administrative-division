from selenium import webdriver
import time
import pymysql

class GovementSpider:
    def __init__(self):
        self.browser = webdriver.Chrome()
        self.one_url = 'http://www.mca.gov.cn/article/sj/xzqh/2020/'
        self.db = pymysql.connect(
            'localhost', 'root', '12345678', 'govdb', charset='utf8'
        )
        self.cursor = self.db.cursor()

    #获取首页，提取二级页面链接（虚假链接）
    def get_false_url(self):
        self.browser.get(url=self.one_url)
        #提取二级页面链接 + 点击该节点
        td_list = self.browser.find_elements_by_xpath(
            '//td[@class="arlisttd"]/a[contains(@title,"行政区划代码")]'
        )
        if td_list:
            #找节点对象，访问二级页面时直接click()
            two_url_element = td_list[0]
            #获取虚假二级链接，比对version实现增量爬取
            two_url = two_url_element.get_attribute('href')
            sel = 'select * from version where link = %s'
            self.cursor.execute(sel,[two_url])
            if self.cursor.fetchall():
                print('数据为最新，无需更新')
            else:
                #点击进入二级页面
                two_url_element.click()
                time.sleep(3)
                #切换broeser
                all_handles = self.browser.window_handles
                self.browser.switch_to_window(all_handles[1])
                #数据抓取
                self.get_data()
                # 爬取结束后把two_url插入version
                ins = 'insert into version VALUES (%s)'
                self.cursor.execute(ins,[two_url])
                self.db.commit()


    #二级页面提取编码
    def get_data(self):
        #基准xpth
        tr_list = self.browser.find_elements_by_xpath('//tr[@height="19"]')
        self.province_list = []
        self.city_list = []
        self.county_list = []
        for tr in tr_list:
            code = tr.find_element_by_xpath('./td[2]').text.strip()
            name = tr.find_element_by_xpath('./td[3]').text.strip()
            print(name,code)
            #判断层级关系，添加至对应数据库表
            #province
            if code[-4:] == '0000':
                self.province_list.append([name,code])
                #将直辖市放入 city_list
                if '市' in name:
                    self.city_list.append([name,code,code])
            #city   不含直辖市
            elif code[-2:] =='00':
                self.city_list.append([name,code,code[:2]+'0000'])
            #county
            else:
                # 直辖市区县
                if code[:2] in ('11','12','31','50'):
                    self.county_list.append([name,code,code[:2]+'0000'])
                # 普通城市区县
                else:
                    self.county_list.append([name,code,code[:4]+'00'])
        self.insert_mysql()

    def insert_mysql(self):
        #删除之前的数据
        ins = 'delete from county'
        self.cursor.execute(ins)
        ins = 'delete from city'
        self.cursor.execute(ins)
        ins = 'delete from province'
        self.cursor.execute(ins)
        #插入新数据
        ins_province = 'insert into province VALUES (%s,%s)'
        ins_city = 'insert into city VALUES (%s,%s,%s)'
        ins_county = 'insert into county VALUES (%s,%s,%s)'
        self.cursor.executemany(ins_province,self.province_list)
        self.cursor.executemany(ins_city,self.city_list)
        self.cursor.executemany(ins_county,self.county_list)

        self.db.commit()
        print('数据抓取完成，成功存入数据库')

    def main(self):
        self.get_false_url()
        self.cursor.close()
        self.db.close()
        self.browser.quit()


if __name__ == '__main__':
    spider = GovementSpider()
    spider.main()
