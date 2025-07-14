from django.db import models

# Create your models here.

class Auto(models.Model):
    DIRECCIONES = [
        ('N', 'Norte a Sur'),
        ('S', 'Sur a Norte'),
    ]
    nombre = models.CharField(max_length=50)
    velocidad = models.FloatField()
    tiempo_espera = models.FloatField()
    direccion = models.CharField(max_length=1, choices=DIRECCIONES)
    en_puente = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.get_direccion_display()})"
