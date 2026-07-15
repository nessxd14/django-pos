from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    Cliente,
    DetalleVenta,
    MetodoPago,
    MovimientoInventario,
    Pago,
    PerfilEmpleado,
    Producto,
    SesionCaja,
    Venta,
)


ROLES_POS = {
    PerfilEmpleado.Rol.MAYORISTA,
    PerfilEmpleado.Rol.VENDEDOR,
    PerfilEmpleado.Rol.CAJA,
    PerfilEmpleado.Rol.ADMINISTRACION,
}


def usuario_puede_vender(usuario):
    if usuario.is_superuser:
        return True
    perfil = getattr(usuario, 'perfil_retail', None)
    return bool(perfil and perfil.activo and perfil.rol in ROLES_POS)


def crear_venta_pos(usuario, datos):
    if not usuario_puede_vender(usuario):
        raise ValidationError('El usuario no tiene permiso para usar el POS.')

    items = datos.get('items') or []
    if not items:
        raise ValidationError('Agrega al menos un producto a la venta.')

    canal = datos.get('canal') or Venta.Canal.MOSTRADOR
    if canal not in Venta.Canal.values:
        raise ValidationError('Canal de venta invalido.')

    with transaction.atomic():
        cliente = _obtener_cliente(datos.get('cliente_id'), canal)
        metodo_pago = _obtener_metodo_pago(datos.get('metodo_pago_id'))

        if metodo_pago.tipo == MetodoPago.Tipo.CREDITO and cliente is None:
            raise ValidationError('El pago a credito requiere un cliente.')

        sesion_caja = _obtener_sesion_caja(datos.get('sesion_caja_id'), usuario)
        venta = Venta.objects.create(
            numero=generar_numero_venta(),
            canal=canal,
            estado=Venta.Estado.BORRADOR,
            cliente=cliente,
            vendedor=usuario,
            cajero=usuario,
            sesion_caja=sesion_caja,
            notas=(datos.get('notas') or '').strip(),
        )

        for item in items:
            _crear_detalle_desde_item(venta, item, usuario)

        venta.descuento = _decimal(datos.get('descuento'), 'descuento')
        venta.recalcular_totales()

        if venta.descuento > venta.subtotal:
            raise ValidationError('El descuento no puede ser mayor al subtotal.')

        monto_recibido = _decimal(datos.get('monto_recibido', venta.total), 'monto recibido')
        if metodo_pago.tipo != MetodoPago.Tipo.CREDITO and monto_recibido < venta.total:
            raise ValidationError('El monto recibido no cubre el total de la venta.')

        Pago.objects.create(
            venta=venta,
            sesion_caja=sesion_caja,
            metodo_pago=metodo_pago,
            monto=venta.total,
            referencia=(datos.get('referencia') or '').strip(),
            recibido_por=usuario,
        )

        venta.estado = Venta.Estado.PAGADA
        venta.save(update_fields=['estado', 'actualizado_en'])
        return venta


def generar_numero_venta():
    prefijo = timezone.localtime().strftime('V%Y%m%d')
    ultima = Venta.objects.filter(numero__startswith=prefijo).order_by('-numero').first()
    if ultima:
        try:
            correlativo = int(ultima.numero.rsplit('-', 1)[1]) + 1
        except (IndexError, ValueError):
            correlativo = Venta.objects.filter(numero__startswith=prefijo).count() + 1
    else:
        correlativo = 1
    return f'{prefijo}-{correlativo:04d}'


def _crear_detalle_desde_item(venta, item, usuario):
    try:
        producto_id = int(item.get('producto_id'))
        cantidad = int(item.get('cantidad'))
    except (TypeError, ValueError):
        raise ValidationError('Producto o cantidad invalida.')

    if cantidad <= 0:
        raise ValidationError('La cantidad debe ser mayor a cero.')

    producto = Producto.objects.select_for_update().get(pk=producto_id, activo=True)
    if producto.stock_actual < cantidad:
        raise ValidationError(f'Stock insuficiente para {producto.nombre}.')

    precio = producto.precio_para_canal(venta.canal)
    descuento = _decimal(item.get('descuento'), 'descuento de linea')
    if descuento > precio * cantidad:
        raise ValidationError(f'El descuento de {producto.nombre} supera el total de la linea.')

    DetalleVenta.objects.create(
        venta=venta,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=precio,
        descuento=descuento,
    )
    producto.stock_actual -= cantidad
    producto.save(update_fields=['stock_actual', 'actualizado_en'])
    MovimientoInventario.objects.create(
        producto=producto,
        tipo=MovimientoInventario.Tipo.SALIDA,
        cantidad=cantidad,
        referencia=venta.numero,
        venta=venta,
        realizado_por=usuario,
        notas='Salida generada desde POS.',
    )


def _obtener_cliente(cliente_id, canal):
    if not cliente_id:
        if canal == Venta.Canal.MAYORISTA:
            raise ValidationError('El canal mayorista requiere seleccionar un cliente.')
        return None
    return Cliente.objects.get(pk=cliente_id, activo=True)


def _obtener_metodo_pago(metodo_pago_id):
    if not metodo_pago_id:
        raise ValidationError('Selecciona un metodo de pago.')
    return MetodoPago.objects.get(pk=metodo_pago_id, activo=True)


def _obtener_sesion_caja(sesion_caja_id, usuario):
    if sesion_caja_id:
        return SesionCaja.objects.get(pk=sesion_caja_id, estado=SesionCaja.Estado.ABIERTA)

    return (
        SesionCaja.objects.filter(cajero=usuario, estado=SesionCaja.Estado.ABIERTA)
        .select_related('caja')
        .first()
    )


def _decimal(valor, campo):
    if valor in (None, ''):
        return Decimal('0.00')
    try:
        numero = Decimal(str(valor)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        raise ValidationError(f'El campo {campo} no es un numero valido.')
    if numero < Decimal('0.00'):
        raise ValidationError(f'El campo {campo} no puede ser negativo.')
    return numero
