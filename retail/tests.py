from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Categoria, DetalleVenta, MetodoPago, MovimientoInventario, Pago, Producto, Venta
from .services import crear_venta_pos


class VentaModelTests(TestCase):
    def test_detalle_usa_precio_mayorista_y_recalcula_total(self):
        usuario = get_user_model().objects.create_user(username='vendedor', password='test12345')
        categoria = Categoria.objects.create(nombre='Papeleria')
        producto = Producto.objects.create(
            sku='BOL-001',
            nombre='Boligrafo azul',
            categoria=categoria,
            precio_compra=Decimal('1.00'),
            precio_venta=Decimal('2.50'),
            precio_mayorista=Decimal('2.00'),
            stock_actual=100,
        )
        venta = Venta.objects.create(
            numero='V-0001',
            canal=Venta.Canal.MAYORISTA,
            vendedor=usuario,
        )

        DetalleVenta.objects.create(venta=venta, producto=producto, cantidad=3)
        venta.refresh_from_db()

        self.assertEqual(venta.subtotal, Decimal('6.00'))
        self.assertEqual(venta.total, Decimal('6.00'))

    def test_pos_crea_venta_pagada_y_descuenta_stock(self):
        usuario = get_user_model().objects.create_user(username='caja', password='test12345')
        categoria = Categoria.objects.create(nombre='Utiles escolares')
        producto = Producto.objects.create(
            sku='CUA-001',
            nombre='Cuaderno universitario',
            categoria=categoria,
            precio_compra=Decimal('5.00'),
            precio_venta=Decimal('10.00'),
            precio_mayorista=Decimal('8.00'),
            stock_actual=12,
        )
        metodo_pago = MetodoPago.objects.create(nombre='Efectivo', tipo=MetodoPago.Tipo.EFECTIVO)

        venta = crear_venta_pos(
            usuario,
            {
                'canal': Venta.Canal.MOSTRADOR,
                'metodo_pago_id': metodo_pago.id,
                'monto_recibido': '25.00',
                'items': [
                    {'producto_id': producto.id, 'cantidad': 2, 'descuento': '0.00'},
                ],
            },
        )

        producto.refresh_from_db()
        self.assertEqual(venta.estado, Venta.Estado.PAGADA)
        self.assertEqual(venta.total, Decimal('20.00'))
        self.assertEqual(producto.stock_actual, 10)
        self.assertEqual(Pago.objects.get(venta=venta).monto, Decimal('20.00'))
        self.assertTrue(
            MovimientoInventario.objects.filter(
                venta=venta,
                producto=producto,
                tipo=MovimientoInventario.Tipo.SALIDA,
                cantidad=2,
            ).exists(),
        )
