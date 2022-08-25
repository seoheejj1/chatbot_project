from django.shortcuts import render
import pymysql
import pymysql.cursors
from functools import reduce
import sys
sys.path.append('../')
from crawl.crawl import Crawl

DB_HOST = "localhost"
DB_USER = "myuser118"
DB_PASSWORD = "1234"
DB_NAME = "mydb118"

crawl = Crawl()


def home(req):
    return render(req, 'home.html')


def rubybot(req):
    return render(req, 'rubybot.html')


def ppukkubot(req):
    return render(req, 'ppukkubot.html')


def pstorage(req):
    content = {}

    database = None
    try:
        database = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            passwd=DB_PASSWORD,
            db=DB_NAME,
            charset='utf8'
        )

        sql = f'''
                select * from danbee_query as a , danbee_rest as b where a.ins_id = b.ins_id;
            '''

        with database.cursor() as cursor:
            cursor.execute(sql)
            danbee_rest = cursor.fetchall()
            content['danbee_rest'] = reduce(
                lambda a, b: a.append(reduce(lambda c, d: c.append(d) or c if d != None else c.append('') or c, b, [])) or a, danbee_rest, [])

        sql = f'''
                select * from danbee_query as a , danbee_menu as b where a.ins_id = b.ins_id;
            '''

        with database.cursor() as cursor:
            cursor.execute(sql)
            danbee_menu = cursor.fetchall()
            content['danbee_menu'] = danbee_menu

    except Exception as e:
        print(e)

    finally:
        if database is not None:
            database.close()

    return render(req, 'pstorage.html', content)


def storage(req):
    content = {}

    database = None
    try:
        database = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            passwd=DB_PASSWORD,
            db=DB_NAME,
            charset='utf8'
        )

        # 주식 조회 목록
        sql = f'''
                select * from chatbot_view ORDER BY date DESC
            '''
        with database.cursor() as cursor:
            cursor.execute(sql)
            chatbot_view = cursor.fetchall()
            content['chatbot_view'] = chatbot_view

         # 날짜별 환율 목록
        sql = f'''
                select * from chatbot_eor ORDER BY view DESC
            '''
        with database.cursor() as cursor:
            cursor.execute(sql)
            chatbot_eor = cursor.fetchall()
            content['chatbot_eor'] = chatbot_eor

        # 오늘의 증시 목록
        sql = f'''
                select * from chatbot_stock_today ORDER BY view DESC
            '''
        with database.cursor() as cursor:
            cursor.execute(sql)
            chatbot_stock_today = cursor.fetchall()
            content['chatbot_stock_today'] = chatbot_stock_today

        # 거래 목록
        sql = f'''
                select * from chatbot_order ORDER BY date DESC
            '''
        with database.cursor() as cursor:
            cursor.execute(sql)
            chatbot_order = cursor.fetchall()
            content['chatbot_order'] = chatbot_order

        # 보유주 리스트
        sql = f'''
                select code, name, sum(sum), sum(total) from (select code, name, sum(amount) as sum, sum(amount * price) as total from chatbot_order where amount > 0 and cancel = 0 group by name UNION select code, name, sum(amount), -1 * sum(amount * price) from chatbot_order where amount < 0 and cancel = 0 group by name) as a group by name having sum(sum) > 0
            '''
        with database.cursor() as cursor:
            cursor.execute(sql)
            chatbot_own = cursor.fetchall()
            eor = float(crawl.eor())
            List = reduce(lambda a, b: a.append(int(crawl.search_engine(b[0])['가격'].replace(',', '') if crawl.search_engine(b[0])['코드']
                                                    in crawl.korea_id else int(float(crawl.search_engine(b[0])['가격']) * eor)) * int(b[2])) or a, chatbot_own, [])
            content['chatbot_own'] = [(chatbot_own[i][0], chatbot_own[i][1], int(
                chatbot_own[i][2]), int(chatbot_own[i][3]), List[i], f'{(List[i] / int(chatbot_own[i][3]) * 100) - 100:.2f}%') for i in range(len(chatbot_own))]
            content['chatbot_total'] = sum(
                [int(total) for code, name, cnt, total in chatbot_own])
            content['chatbot_current_total'] = sum(List)
            content['chatbot_profit_loss'] = sum(
                List) - content['chatbot_total']

    except Exception as e:
        print(e)

    finally:
        if database is not None:
            database.close()

    return render(req, 'storage.html', content)


def del_view(req, table):
    database = None
    try:
        database = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            passwd=DB_PASSWORD,
            db=DB_NAME,
            charset='utf8'
        )

        sql = f'''
                delete from {table}
            '''
        with database.cursor() as cursor:
            cursor.execute(sql)
            print('삭제')
            database.commit()

    except Exception as e:
        print(e)

    finally:
        if database is not None:
            database.close()

    return render(req, 'storage.html')


def send_ppukku(req):
    if 'intent_id' in req.GET:
        if req.GET['intent_id'] == 'a95d62d3-14af-418d-9446-18badadac937':
            intent = '메뉴추천'
        elif req.GET['intent_id'] == '2fb157ca-7d1a-4751-894b-96d2eacf3bd7':
            intent = '맛집추천'
        else:
            intent = '인사'

    database = None
    try:
        database = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            passwd=DB_PASSWORD,
            db=DB_NAME,
            charset='utf8'
        )

        if 'genre' in req.GET:
            sql = '''
                INSERT INTO danbee_rest(ins_id, genre) VALUES ('%s', '%s')
            ''' % (req.GET['ins_id'], req.GET['genre'])

        elif 'region' in req.GET:
            sql = '''
                UPDATE danbee_rest SET region = '%s' where ins_id = '%s'
            ''' % (req.GET['region'], req.GET['ins_id'])

        elif 'img' in req.GET:
            sql = '''
                UPDATE danbee_rest SET place_img = '%s', place_name = '%s', place_adr = '%s', place_call = '%s', place_loc = '%s' where ins_id = '%s'
            ''' % (req.GET['img'], req.GET['name'], req.GET['adr'], req.GET['call'], req.GET['loc'], req.GET['ins_id'])

        elif 'population' in req.GET:
            sql = '''
                UPDATE danbee_rest SET population = '%s' where ins_id = '%s'
            ''' % (req.GET['population'], req.GET['ins_id'])
        
        elif 'day' in req.GET:
            sql = '''
                UPDATE danbee_rest SET day = '%s' where ins_id = '%s'
            ''' % (req.GET['day'], req.GET['ins_id'])
        
        elif 'time' in req.GET:
            sql = '''
                UPDATE danbee_rest SET time = '%s' where ins_id = '%s'
            ''' % (req.GET['time'], req.GET['ins_id'])

        elif 'reservation' in req.GET:
            sql = '''
                UPDATE danbee_rest SET reservation = '%s' where ins_id = '%s'
            ''' % (True, req.GET['ins_id'])

        elif 'food1' in req.GET:
            sql = '''
                INSERT INTO danbee_menu(ins_id, food1) VALUES ('%s', '%s')
            ''' % (req.GET['ins_id'], req.GET['food1'])

        elif 'food2' in req.GET:
            sql = '''
                UPDATE danbee_menu SET food2 = '%s' where ins_id = '%s'
            ''' % (req.GET['food2'], req.GET['ins_id'])

        elif 'food3' in req.GET:
            sql = '''
                UPDATE danbee_menu SET food3 = '%s' where ins_id = '%s'
            ''' % (req.GET['food3'], req.GET['ins_id'])

        elif 'food4' in req.GET:
            sql = '''
                UPDATE danbee_menu SET food4 = '%s' where ins_id = '%s'
            ''' % (req.GET['food4'], req.GET['ins_id'])

        elif 'food5' in req.GET:
            sql = '''
                UPDATE danbee_menu SET food5 = '%s' where ins_id = '%s'
            ''' % (req.GET['food5'], req.GET['ins_id'])

        elif 'food_result' in req.GET:
            sql = '''
                UPDATE danbee_menu SET food_result = '%s' where ins_id = '%s'
            ''' % (req.GET['food_result'], req.GET['ins_id'])

        else:
            sql = '''
                INSERT INTO danbee_query(ins_id, intent, query, answer) VALUES ('%s', '%s', '%s', '%s')
            ''' % (req.GET['ins_id'], intent, req.GET['input'], req.GET['answer'])

        with database.cursor() as cursor:
            cursor.execute(sql)
            print('저장')
            database.commit()

    except Exception as e:
        print(e)

    finally:
        if database is not None:
            database.close()

    return render(req, 'ppukkubot.html')
