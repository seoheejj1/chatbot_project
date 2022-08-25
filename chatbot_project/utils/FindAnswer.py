class FindAnswer:
    def __init__(self, db):
        self.db = db 
    # ② 답변 검색
    def search(self, intent_name, ner_tags):
        sql = self._make_query(intent_name, ner_tags)
        answer = self.db.select_one(sql)

        if answer is None:
            sql = self._make_query(intent_name, None)
            answer = self.db.select_one(sql)
        return answer['answer']
    
    # ③ 검색 쿼리 생성
    def _make_query(self, intent_name, ner_tags):
        sql = "select * from chatbot_query"
        if intent_name != None and ner_tags == None:
            sql = sql + \
                f" where intent = '{intent_name}' "
        elif intent_name != None and ner_tags != None:
            where = f" where intent = (select intent from chatbot where intent = '{intent_name}'"
            if (len(ner_tags) > 0):
                where += 'and ('
                for ner in ner_tags:
                    where += f" ner like '%{ner}%' or "
                where = where[:-3] + ')'
            sql = sql + where + ')'
        return sql       
    
    def tag_to_word(self, ner_predicts, answer):    
        for word, tag in ner_predicts:

            if tag == 'B_STOCK' or tag == 'B_COUNT':
                answer = answer.replace(tag, word)

        answer = answer.replace('{', '')
        answer = answer.replace('}', '')
        return answer