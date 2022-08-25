import threading
import json
import re
import pymysql
import pymysql.cursors
from sqlalchemy import true

from config.DatabaseConfig import *
from utils.Database import Database
from utils.BotServer import BotServer
from utils.Preprocess import Preprocess
from models.intent.IntentModel import IntentModel
from models.ner.NerModel import NerModel
from utils.FindAnswer import FindAnswer
from crawl.crawl import Crawl

p1 = Preprocess(
    word2index_dic='train_tools/dict/chatbot_dict_intent.bin',
    userdic='utils/user_dic.tsv'
)

p2 = Preprocess(
    word2index_dic='train_tools/dict/chatbot_dict_ner.bin',
    userdic='utils/user_dic.tsv'
)

intent = IntentModel(
    model_name='models/intent/intent_model.h5',
    preprocess=p1
)

ner = NerModel(
    model_name='models/ner/ner_model.h5',
    preprocess=p2
)

crawl = Crawl()

code_to_event = {b: a for a, b in crawl.event_to_code.items()}


def to_client(conn, addr, params):
    db = params['db']
    try:
        db.connect()

        read = conn.recv(4096)
        print('===========================')
        print('Connection from: %s' % str(addr))

        if read is None or not read:
            print('클라이언트 연결 끊어짐')
            exit(0)

        recv_json_data = json.loads(read.decode())
        print("데이터 수신 :", recv_json_data)
        query = recv_json_data['Query']

        trade_ok = False

        send_json_data_str = {}

        if 'Eor' in recv_json_data:
            database = pymysql.connect(
                host=DB_HOST,
                user=DB_USER,
                passwd=DB_PASSWORD,
                db=DB_NAME,
                charset='utf8'
            )
            try:
                sql = '''
                    INSERT chatbot_eor(country, eor) 
                    values(
                    '%s', '%s'
                    )
                ''' % (query, recv_json_data['Eor'])

                sql = sql.replace("'None'", "null")

                with database.cursor() as cursor:
                    cursor.execute(sql)
                    print('저장')
                    database.commit()

            except Exception as e:
                print(e)

            finally:
                if database is not None:
                    database.close()

            send_json_data_str['country'] = re.sub('[0-9|A-Z| ]*', '', query)
            send_json_data_str['Answer'] = send_json_data_str['country'] + ' 환율이다 냥'
            send_json_data_str['currency'] = re.sub('[^A-Z]*', '', query)
            send_json_data_str['eor'] = recv_json_data['Eor'].replace(',', '')
            send_json_data_str['unit'] = re.sub('[^0-9]*', '', query)

            message = json.dumps(send_json_data_str)
            conn.send(message.encode())
            return
        elif 'Cancel' in recv_json_data:
            database = None
            try:
                database = pymysql.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    passwd=DB_PASSWORD,
                    db=DB_NAME,
                    charset='utf8'
                )

                sql = '''
                    UPDATE chatbot_order set cancel = 1 where id = '%s'
                ''' % (recv_json_data['Cancel'])

                with database.cursor() as cursor:
                    cursor.execute(sql)
                    print('저장')
                    database.commit()

                send_json_data_str['Answer'] = query.strip()

            except Exception as e:
                print(e)

            finally:
                if database is not None:
                    database.close()

            message = json.dumps(send_json_data_str)
            conn.send(message.encode())
            return

        elif 'Word' in recv_json_data:
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
                        select * from chatbot_word where word = '{recv_json_data['Word']}'
                    '''
                with database.cursor() as cursor:
                    cursor.execute(sql)

                    send_json_data_str['Answer'] = f"{recv_json_data['Word']}에 대한 설명이다냥"
                    send_json_data_str['explain'] = cursor.fetchone()

            except Exception as e:
                print(e)

            finally:
                if database is not None:
                    database.close()

            message = json.dumps(send_json_data_str)
            conn.send(message.encode())
            return

        elif 'Selection' in recv_json_data:
            send_json_data_str['Answer'] = "하고싶은 것을 선택해달라 냥"
            send_json_data_str['list'] = ['정보 조회', '매수', '매도', '취소']
            send_json_data_str['event'] = query.strip()

            message = json.dumps(send_json_data_str)
            conn.send(message.encode())
            return

        elif 'Trade' in recv_json_data:
            intent_name = recv_json_data['Intent']
            ner_predicts = [(query.strip(), 'B_STOCK'),
                            (recv_json_data['Trade'] + '개', 'B_COUNT')]
            ner_tags = ['B_STOCK', 'B_COUNT']

        elif re.search(r'용어|단어', query.strip()) != None:
            send_json_data_str = {
                "Answer": "어떤 용어가 궁금하냥?"
            }

            database = None
            try:
                database = pymysql.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    passwd=DB_PASSWORD,
                    db=DB_NAME,
                    charset='utf8'
                )

                sql = '''
                    select * from chatbot_word
                '''

                with database.cursor() as cursor:
                    cursor.execute(sql)

                    send_json_data_str['word'] = [i[0]
                                                  for i in cursor.fetchall()]

            except Exception as e:
                print(e)

            finally:
                if database is not None:
                    database.close()

            message = json.dumps(send_json_data_str)
            conn.send(message.encode())
            return

        elif query.strip() in crawl.foreign_id + crawl.foreign_name + crawl.korea_id + crawl.korea_name:
            result = crawl.search_engine(query.strip())

            if type(result) == str:
                send_json_data_str["Answer"] = result

                message = json.dumps(send_json_data_str)
                conn.send(message.encode())
                return
            elif type(result) == list and len(result) > 1:
                send_json_data_str["Answer"] = "검색된 종목들이다 냥"
                send_json_data_str["many"] = result

                message = json.dumps(send_json_data_str)
                conn.send(message.encode())
                return
            else:
                send_json_data_str['Answer'] = "하고싶은 것을 선택해달라 냥"
                send_json_data_str['list'] = ['정보 조회', '매수', '매도', '취소']
                send_json_data_str['event'] = query.strip()

                message = json.dumps(send_json_data_str)
                conn.send(message.encode())
                return

        else:
            intent_predict = intent.predict_class(query.strip())
            intent_name = intent.labels[intent_predict]

            ner_predicts = [(x, 'B_STOCK') if (x in crawl.foreign_id + crawl.foreign_name + crawl.korea_id + crawl.korea_name) and y != 'B_STOCK' else (x, y) for x, y in [(a, 'O') if a not in crawl.foreign_id + crawl.foreign_name +
                                                                                                                                                                           crawl.korea_id + crawl.korea_name and b == 'B_STOCK' else (a, b) for a, b in [(i, 'B_COUNT') if re.match(r'^\d+주$', i) != None and j != 'B_COUNT' else (i, j) for i, j in ner.predict(query.strip())]]]
            ner_tags = [j for i, j in ner_predicts if j ==
                        'B_STOCK' or j == 'B_COUNT']

        print("의도 :", intent_name)
        print("개체명 :", ner_predicts)

        if ner_tags.count('B_STOCK') > 1:
            message = json.dumps({"Answer": "종목을 하나만 입력해달라 냥!!!"})

            conn.send(message.encode())
            return

        elif ner_tags.count('B_COUNT') > 1:
            message = json.dumps({"Answer": "갯수를 하나만 입력해달라 냥!!!"})

            conn.send(message.encode())
            return

        try:
            f = FindAnswer(db)
            answer_text = f.search(intent_name, ner_tags)
            answer = f.tag_to_word(ner_predicts, answer_text)

        except:
            answer = "DB에서 정보를 찾을 수 없다 냥!!!!!"

        send_json_data_str = {
            "Query": query.strip(),
            "Answer": answer
        }

        database = None
        try:
            database = pymysql.connect(
                host=DB_HOST,
                user=DB_USER,
                passwd=DB_PASSWORD,
                db=DB_NAME,
                charset='utf8'
            )
            sql = ''

            if intent_name == '특정 주가 조회':
                stock = None
                for word, cls in ner_predicts:
                    if cls == "B_STOCK" and stock == None:
                        stock = word

                if stock == None:
                    send_json_data_str["Answer"] = "종목명을 정확하게 알려달라냥"

                else:
                    result = crawl.search_engine(stock)

                    if type(result) == str:
                        send_json_data_str["Answer"] = result
                    else:
                        if type(result) == list:
                            result = crawl.search_engine(
                                [a for a, b, c in crawl.content if c == stock][0])

                        send_json_data_str["information"] = result

                        sql = '''
                            INSERT chatbot_view(code, name, price, hp, lp, yp, mp, total_mp, tc, max_p, min_p, amount, graph) 
                            values(
                            '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s'
                            )
                        ''' % (
                            result["코드"],
                            result["종목"],
                            result["가격"],
                            result["고가"],
                            result["저가"],
                            result["전일종가"],
                            result["시가"] if "시가" in result else "",
                            result["시가총액"] if "시가총액" in result else "",
                            result["거래대금"] if "거래대금" in result else "",
                            result["상한가"] if "상한가" in result else "",
                            result["하한가"] if "하한가" in result else "",
                            result["거래량"],
                            result["그래프"]
                        )

            elif intent_name == '환율 계산':
                send_json_data_str["Answer"] = "원하는 환율을 선택해달라 냥"
                send_json_data_str["eor_finder"] = crawl.eor_finder()

                message = json.dumps(send_json_data_str)

                conn.send(message.encode())
                return

            elif intent_name == '오늘의 증시 조회':
                send_json_data_str["stock_today"] = crawl.stock_today()

                sql = '''
                    INSERT chatbot_stock_today(
                        kospi_rate,
                        kospi_change,
                        kospi_per,
                        kospi_graph,
                        kosdaq_rate,
                        kosdaq_change,
                        kosdaq_per,
                        kosdaq_graph,
                        kospi200_rate,
                        kospi200_change,
                        kospi200_per,
                        kospi200_graph
                    ) VALUES (
                        '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s'
                    )
                ''' % (
                    send_json_data_str["stock_today"]["KOSPI"]["지수"],
                    send_json_data_str["stock_today"]["KOSPI"]["변화"],
                    send_json_data_str["stock_today"]["KOSPI"]["변화퍼센트"],
                    send_json_data_str["stock_today"]["KOSPI"]["그래프"],
                    send_json_data_str["stock_today"]["KOSDAQ"]["지수"],
                    send_json_data_str["stock_today"]["KOSDAQ"]["변화"],
                    send_json_data_str["stock_today"]["KOSDAQ"]["변화퍼센트"],
                    send_json_data_str["stock_today"]["KOSDAQ"]["그래프"],
                    send_json_data_str["stock_today"]["KOSPI200"]["지수"],
                    send_json_data_str["stock_today"]["KOSPI200"]["변화"],
                    send_json_data_str["stock_today"]["KOSPI200"]["변화퍼센트"],
                    send_json_data_str["stock_today"]["KOSPI200"]["그래프"]
                )

            elif intent_name == '인기 종목':
                send_json_data_str["hot"] = crawl.top_today()

            elif intent_name == '매수' or intent_name == '매도':
                b_stock = [i for i, j in ner_predicts if j == 'B_STOCK']

                if len(b_stock) < 1:
                    send_json_data_str["Answer"] = "종목명을 정확하게 알려달라냥"

                elif len([i for i, j in ner_predicts if j == 'B_COUNT']) < 1:
                    send_json_data_str["Answer"] = "갯수를 정확하게 알려달라냥"

                else:
                    result = crawl.search_engine(b_stock[0])
                    b_count = [i for i, j in ner_predicts if j ==
                               'B_COUNT'][0][:-1]

                    if not b_count.isdigit():
                        send_json_data_str["Answer"] = "정확한 숫자를 입력해달라 냥"
                    elif int(b_count) <= 0:
                        send_json_data_str["Answer"] = "1 이상의 숫자만 입력해달라 냥"
                    else:
                        if type(result) == str:
                            send_json_data_str["Answer"] = result
                        elif type(result) == list:
                            result = crawl.search_engine(
                                [a for a, b, c in crawl.content if c == b_stock[0]][0])

                        if intent_name == '매도':
                            sql = f'''
                                select sum(amount) from chatbot_order where code = '{result['코드']}' and cancel = 0
                            '''
                            with database.cursor() as cursor:
                                cursor.execute(sql)
                                all_count = cursor.fetchone()[0]

                            if all_count == None or all_count < int(b_count):
                                send_json_data_str = {
                                    "Answer": "보유주가 부족해서 매도가 불가능하다 냥!!"}
                                
                                message = json.dumps(send_json_data_str)

                                conn.send(message.encode())
                                return

                        if result['코드'] not in crawl.foreign_id:
                            sql = '''
                                INSERT chatbot_order(code, name, amount, price) 
                                values(
                                '%s', '%s', '%s', '%s'
                                )
                            ''' % (
                                result['코드'],
                                result['종목'],
                                int(b_count) if intent_name == '매수' else -
                                1 * int(b_count),
                                int(re.sub('[^\d]', '', result['가격'])) if intent_name == '매수' else -1 * int(
                                    re.sub('[^\d]', '', result['가격']))
                            )

                            trade_ok = True
                            
                        else:
                            eor = crawl.eor()

                            sql = '''
                                INSERT chatbot_order(code, name, amount, price) 
                                values(
                                '%s', '%s', '%s', '%s'
                                )
                            ''' % (
                                result['코드'],
                                result['종목'],
                                int(b_count) if intent_name == '매수' else - 1 * int(b_count),
                                int(float(result['가격']) * float(eor)) if intent_name == '매수' else -1 * int(
                                    float(result['가격']) * float(eor))
                            )

                            trade_ok = True

            elif intent_name == '주문 취소':
                b_stock = [i for i, j in ner_predicts if j == 'B_STOCK']

                if len(b_stock) < 1:
                    send_json_data_str["Answer"] = "종목명을 정확하게 알려달라냥"
                else:
                    sql = f'''
                        select id, code, name, amount, price from chatbot_order where cancel = 0 and 0 <= (select sum(amount) from chatbot_order where (name = '{b_stock[0]}' or code = '{b_stock[0]}') and cancel = 0) - amount and (name = '{b_stock[0]}' or code = '{b_stock[0]}')
                    '''

                    with database.cursor() as cursor:
                        cursor.execute(sql)
                        order_list = cursor.fetchall()
                        if len(order_list) > 0:
                            send_json_data_str['Answer'] = '취소하고 싶은 것을 선택해달라 냥'
                            send_json_data_str['order_list'] = order_list
                        else:
                            send_json_data_str['Answer'] = f'{b_stock[0]}에서 취소할 수 있는 주문이 없다 냥'

            if sql != '':
                sql = sql.replace("'None'", "null")

                with database.cursor() as cursor:
                    cursor.execute(sql)
                    print('저장')
                    database.commit()

            if trade_ok:
                sql = f'''
                    select code, name, sum(amount) from chatbot_order where code = '{result['코드']}' and name = '{result['종목']}'
                '''

                with database.cursor() as cursor:
                    cursor.execute(sql)
                    send_json_data_str['show_me_own'] = [str(i) for i in cursor.fetchone(
                    )] + [int(b_count) if intent_name == '매수' else - 1 * int(b_count)]

        except Exception as e:
            print(e)

        finally:
            if database is not None:
                database.close()

        message = json.dumps(send_json_data_str)

        conn.send(message.encode())

    except Exception as ex:
        print(ex)

    finally:
        if db is not None:
            db.close()
        conn.close()


if __name__ == '__main__':
    db = Database(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db_name=DB_NAME
    )
    print("DB 접속")

    port = 5050
    listen = 100

    bot = BotServer(port, listen)
    bot.create_sock()
    print("bot start")

    while True:
        conn, addr = bot.ready_for_client()

        params = {
            "db": db
        }
        
        client = threading.Thread(target=to_client, args=(
            conn,
            addr,
            params
        ))

        client.start()
