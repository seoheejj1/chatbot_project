import tensorflow as tf
from tensorflow.keras.models import Model, load_model
from tensorflow.keras import preprocessing


# 의도 분류 모델 모듈
class IntentModel:
    def __init__(self, model_name, preprocess):

        # 의도 클래스 별 레이블
        self.labels = {
            0: "인사",
            1: "특정 주가 조회",
            2: "오늘의 증시 조회",
            3: "인기 종목",
            4: "환율 계산",
            5: "매도",
            6: "매수",
            7: "주문 취소",
            8: "전문용어",
            9: "욕설"
        }

        # 의도 분류 모델 불러오기
        self.model = load_model(model_name)

        # 챗봇 Preprocess 객체
        self.p = preprocess

    # 의도 클래스 예측

    def predict_class(self, query):
        # 형태소 분석
        pos = self.p.pos(query)

        # 문장내 키워드 추출(불용어 제거)
        keywords = self.p.get_keywords(pos, without_tag=True)
        sequences = [self.p.get_wordidx_sequence(keywords)]

        # 패딩처리
        padded_seqs = preprocessing.sequence.pad_sequences(
            sequences, maxlen=10, padding='post')

        predict = self.model.predict(padded_seqs)

        predict_class = tf.math.argmax(predict, axis=1)

        return predict_class.numpy()[0]
