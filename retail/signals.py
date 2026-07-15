from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import DetalleVenta, PerfilEmpleado


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_empleado(sender, instance, created, **kwargs):
    if created:
        PerfilEmpleado.objects.get_or_create(usuario=instance)


@receiver(post_save, sender=DetalleVenta)
@receiver(post_delete, sender=DetalleVenta)
def recalcular_totales_venta(sender, instance, **kwargs):
    instance.venta.recalcular_totales()
