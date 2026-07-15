from django.db import models

# Create your models here.
class Facultad(models.Model):
    nombre_facultad = models.CharField(max_length=100)
    code_facultad = models.CharField(max_length=15)
    def __str__(self):
        return self.nombre_facultad
    