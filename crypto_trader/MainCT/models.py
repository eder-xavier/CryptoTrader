from django.db import models

class BuscaHistorico(models.Model):
    query = models.CharField(max_length=200)
    data = models.DateTimeField(auto_now_add=True)
    resultados = models.JSONField()  # Armazena os resultados da API

    def __str__(self):
        return f"{self.query} - {self.data}"