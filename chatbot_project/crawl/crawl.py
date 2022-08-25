from config.DatabaseConfig import *
import pymysql
import pymysql.cursors
from bs4 import BeautifulSoup
import requests


class Crawl:
    def __init__(self):
        self.url = 'https://finance.naver.com/'

        try:
            db = pymysql.connect(
                host=DB_HOST,
                user=DB_USER,
                passwd=DB_PASSWORD,
                db=DB_NAME,
                charset='utf8'
            )

            sql = '''
                select * from chatbot_stock
            '''

            with db.cursor() as cursor:
                cursor.execute(sql)
                content = cursor.fetchall()
                self.content = content
                self.event_to_code = {c: a for a, b, c in content}
                self.korea_name = [c for a, b, c in content if b == '국내주식']
                self.korea_id = [a for a, b, c in content if b == '국내주식']
                self.foreign_name = [c for a, b, c in content if b == '해외주식']
                self.foreign_id = [a for a, b, c in content if b == '해외주식']

        except Exception as e:
            print(e)

        finally:
            if db is not None:
                db.close()

    def top_today(self):
        top = BeautifulSoup(requests.get(self.url).text,
                            'html.parser').select_one("#_topItems1")

        cr_list = top.select('#_topItems1 > tr')

        dic = {}

        for cr_lists in cr_list:
            dic[cr_lists.select_one('th > a').text.strip()] = {
                '종목': cr_lists.select_one('th > a').text.strip(),
                '코드': cr_lists.select_one('th > a').attrs['href'][-6:],
                '가격': cr_lists.select_one('td').text.strip(),
                '변동': cr_lists.select_one('td ~ td span').text.strip(),
                '변동퍼센트': cr_lists.select_one('td ~ td ~td').text.strip()
            }

        return dic

    def stock_today(self):
        kospi = BeautifulSoup(requests.get(self.url).text,
                              'html.parser').select_one(".kospi_area")
        kosdaq = BeautifulSoup(requests.get(self.url).text,
                               'html.parser').select_one(".kosdaq_area")
        kospi200 = BeautifulSoup(requests.get(self.url).text,
                                 'html.parser').select_one(".kospi200_area")

        dic = {
            'KOSPI': {
                '종목': kospi.select_one(".blind").text.strip(),
                '지수': kospi.select_one(".num").text.strip(),
                '변화': kospi.select_one(".num2").text.strip(),
                '변화퍼센트': kospi.select_one(".num3").text.strip(),
                '그래프': kospi.select_one("img[alt='코스피지수 상세보기']").attrs['src']
            },
            'KOSDAQ': {
                '종목': kosdaq.select_one(".blind").text.strip(),
                '지수': kosdaq.select_one(".num").text.strip(),
                '변화': kosdaq.select_one(".num2").text.strip(),
                '변화퍼센트': kosdaq.select_one(".num3").text.strip(),
                '그래프': kosdaq.select_one("img[alt='코스닥지수 상세보기']").attrs['src']
            },
            'KOSPI200': {
                '종목': kospi200.select_one(".blind").text.strip(),
                '지수': kospi200.select_one(".num").text.strip(),
                '변화': kospi200.select_one(".num2").text.strip(),
                '변화퍼센트': kospi200.select_one(".num3").text.strip(),
                '그래프': kospi200.select_one("img[alt='코스피200지수 상세보기']").attrs['src']
            }
        }

        return dic

    def search_engine(self, query):
        if query in self.korea_id:
            return Crawl().search_korea(f'https://finance.naver.com/item/main.naver?code={query}')

        elif query in self.korea_id + self.korea_name:
            query = str(query.encode('euc-kr'))[2:-1].replace('\\x', '%')
            url = f'https://finance.naver.com/search/searchList.naver?query={query}'
            response = requests.get(url)
            dom = BeautifulSoup(response.text, 'html.parser')

            search_list = [(i.text.strip(), i.attrs['href'][-6:])
                           for i in dom.select('td.tit a')]

            if len(search_list) == 0:
                return '검색 결과가 없다 냥'
            elif len(search_list) == 1:
                return Crawl().search_korea(self.url + 'item/main.naver?code=' + search_list[0][-1])

            return search_list

        elif query in self.foreign_id + self.foreign_name:
            alpa = query.replace(" ", "")
            url = f'https://search.naver.com/search.naver?query={alpa}+주가'
            response = requests.get(url)
            dom = BeautifulSoup(response.text, 'html.parser')

            if not dom.find('div', id='_cs_root'):
                if query not in self.foreign_name or query in self.foreign_id:
                    return '검색 결과가 없다 냥'

                else:
                    query = Crawl().event_to_code[query]
                    url = f'https://search.naver.com/search.naver?query={query}+주가'

                    return Crawl().search_foriegn(url)

            else:
                return Crawl().search_foriegn(url)

        else:
            return '검색 결과가 없다 냥'

    def search_korea(self, url):
        try:
            res = BeautifulSoup(requests.get(url).text, 'html.parser')

            rate_info = res.select('.rate_info td span.blind')

            dic = {
                '코드': res.select_one('div.description span.code').text.strip(),
                '종목': res.select_one('div.wrap_company h2 a').text.strip(),
                '가격': res.select_one('p.no_today span.blind').text.strip(),
                '전일종가': rate_info[0].text.strip(),
                '고가': rate_info[1].text.strip(),
                '상한가': rate_info[2].text.strip(),
                '거래량': rate_info[3].text.strip(),
                '시가': rate_info[4].text.strip(),
                '저가': rate_info[5].text.strip(),
                '하한가': ''.join([i.text.strip() for i in res.select('.rate_info td .sp_txt7 ~ em span')]),
                '거래대금': rate_info[6].text.strip() + ' 백만',
                '그래프': res.select_one('#img_chart_area').attrs['src']
            }

            return dic
        except:
            return "국내 주식 검색 중 오류가 났다 냥"

    def search_foriegn(self, url):
        try:
            response = requests.get(url)
            dom = BeautifulSoup(response.text, 'html.parser')
            res = dom.find('div', id='_cs_root')
            event_code = res.select_one('span.stk_nm ~ em.t_nm').text.replace('"', '').strip() if res.select_one(
                'span.stk_nm ~ em.t_nm') != None else res.select_one('span.stk_nm ~ em.t_nm_s').text.replace('"', '').strip()

            dic = {
                '코드': event_code.split(" ")[0],
                '종목': res.select_one('span.stk_nm').text.strip(),
                '가격': res.select_one('span.spt_con strong').text.strip(),
                '전일종가': res.select_one('li.pcp dd').text.strip(),
                '고가': res.select_one('li.hp dd').text.strip(),
                '거래량': res.select_one('li.vl dd').text.strip(),
                '저가': res.select_one('li.lp dd').text.strip(),
                '시가총액': res.select_one('li.cp dl span.spt_con strong').text.strip(),
                '그래프': res.select_one('img._stock_chart').attrs['src']
            }

            return dic
        except:
            return "해외 주식 검색 중 오류가 났다 냥"

    def eor_finder(a):
        url = 'https://finance.naver.com/marketindex/exchangeList.naver'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        dom = BeautifulSoup(response.text, 'html.parser')
        elements = dom.select("tr")[2:]

        return [
            {
                'name': i.select_one('td.tit a').text.strip(),
                'eor': i.select_one('td.sale').text.strip()
            }
            for i in elements
        ]

    def eor(a):
        url = 'https://finance.naver.com/marketindex/exchangeDetail.naver?marketindexCd=FX_USDKRW'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        dom = BeautifulSoup(response.text, 'html.parser')
        elements = dom.select(
            '#content > div.section_calculator > table:nth-child(4) > tbody > tr > td:nth-child(1)')
        usd = elements[0].text.strip()
        usd = usd.replace(',', '')
        return float(usd)
