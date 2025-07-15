from django.db import models
import random

# Create your models here.

class Auto(models.Model):
    DIRECCIONES = [
        ('N', 'Norte a Sur'),
        ('S', 'Sur a Norte'),
    ]
    direccion = models.CharField(max_length=1, choices=DIRECCIONES)
    velocidad = models.FloatField()  # km/h
    turno = models.PositiveIntegerField()
    tiempo_cruce = models.FloatField()  # segundos
    tiempo_espera = models.FloatField()  # segundos
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Auto {self.id} ({self.get_direccion_display()})"
