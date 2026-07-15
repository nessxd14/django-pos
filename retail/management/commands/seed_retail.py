from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from retail.models import Caja, Categoria, MetodoPago, PerfilEmpleado


class Command(BaseCommand):
    help = 'Carga datos base del sistema retail.'

    def handle(self, *args, **options):
        self._crear_grupos()
        self._crear_catalogos_base()
        self.stdout.write(self.style.SUCCESS('Datos base retail cargados.'))

    def _crear_grupos(self):
        permisos_por_rol = {
            PerfilEmpleado.Rol.ADMINISTRACION: Permission.objects.filter(content_type__app_label='retail'),
            PerfilEmpleado.Rol.ALMACEN: self._permisos(
                ['producto', 'categoria', 'proveedor', 'movimientoinventario'],
                ['add', 'change', 'view'],
            ),
            PerfilEmpleado.Rol.MAYORISTA: self._permisos(
                ['producto', 'cliente', 'venta', 'detalleventa'],
                ['add', 'change', 'view'],
            ),
            PerfilEmpleado.Rol.VENDEDOR: self._permisos(
                ['producto', 'cliente', 'venta', 'detalleventa'],
                ['add', 'change', 'view'],
            ),
            PerfilEmpleado.Rol.CAJA: self._permisos(
                ['caja', 'sesioncaja', 'venta', 'pago', 'metodopago'],
                ['add', 'change', 'view'],
            ),
        }

        for rol, permisos in permisos_por_rol.items():
            group, _ = Group.objects.get_or_create(name=f'Retail - {PerfilEmpleado.Rol(rol).label}')
            group.permissions.add(*permisos)
            self.stdout.write(f'Grupo listo: {group.name}')

    def _permisos(self, modelos, acciones):
        codenames = [
            f'{accion}_{modelo}'
            for modelo in modelos
            for accion in acciones
        ]
        return Permission.objects.filter(content_type__app_label='retail', codename__in=codenames)

    def _crear_catalogos_base(self):
        categorias = [
            'Papeleria',
            'Utiles escolares',
            'Articulos de oficina',
            'Tecnologia basica',
        ]
        for nombre in categorias:
            Categoria.objects.get_or_create(nombre=nombre)

        metodos = [
            ('Efectivo', MetodoPago.Tipo.EFECTIVO),
            ('QR', MetodoPago.Tipo.QR),
            ('Tarjeta', MetodoPago.Tipo.TARJETA),
            ('Transferencia', MetodoPago.Tipo.TRANSFERENCIA),
            ('Credito mayorista', MetodoPago.Tipo.CREDITO),
        ]
        for nombre, tipo in metodos:
            MetodoPago.objects.get_or_create(nombre=nombre, defaults={'tipo': tipo})

        Caja.objects.get_or_create(nombre='Caja principal', defaults={'ubicacion': 'Mostrador'})
