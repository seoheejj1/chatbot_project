from django.db import models
from django.forms import IntegerField

# Create your models here.

class Answer(models.Model):
    persona = models.CharField(max_length=3, verbose_name="페르소나")
    intent = models.CharField(max_length=30, verbose_name="의도")
    ner = models.CharField(max_length=60, verbose_name="BIO")
    query = models.CharField(max_length=1200, verbose_name="쿼리")
    answer = models.CharField(max_length=1200, verbose_name="대답")
    answer_image = models.CharField(max_length=1200, verbose_name="대답(이미지)", null=True)