import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import F, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import Caja, Cliente, MetodoPago, Producto, SesionCaja, Venta
from .services import crear_venta_pos, usuario_puede_vender


@login_required
def dashboard(request):
    productos_bajo_stock = Producto.objects.filter(
        activo=True,
        stock_actual__lte=F('stock_minimo'),
    )
    ventas_pagadas = Venta.objects.filter(estado=Venta.Estado.PAGADA)
    contexto = {
        'total_productos': Producto.objects.filter(activo=True).count(),
        'productos_bajo_stock': productos_bajo_stock.count(),
        'ventas_pagadas': ventas_pagadas.count(),
        'ingresos_pagados': ventas_pagadas.aggregate(total=Sum('total'))['total'] or 0,
        'cajas_activas': Caja.objects.filter(activa=True).count(),
        'sesiones_abiertas': SesionCaja.objects.filter(estado=SesionCaja.Estado.ABIERTA).count(),
        'ultimas_ventas': Venta.objects.select_related('cliente', 'vendedor').order_by('-fecha')[:8],
        'productos_alerta': Producto.objects.select_related('categoria').filter(
            activo=True,
            stock_actual__lte=F('stock_minimo'),
        )[:8],
    }
    return render(request, 'retail/dashboard.html', contexto)


@login_required
def pos(request):
    if not usuario_puede_vender(request.user):
        return render(request, 'retail/pos_denegado.html', status=403)

    productos = [
        {
            'id': producto.id,
            'sku': producto.sku,
            'codigo_barra': producto.codigo_barra or '',
            'nombre': producto.nombre,
            'categoria': producto.categoria.nombre,
            'stock_actual': producto.stock_actual,
            'precio_venta': str(producto.precio_venta),
            'precio_mayorista': str(producto.precio_mayorista),
        }
        for producto in Producto.objects.select_related('categoria').filter(activo=True).order_by('nombre')
    ]
    clientes = [
        {
            'id': cliente.id,
            'nombre': cliente.nombre,
            'tipo': cliente.tipo,
            'nit_ci': cliente.nit_ci,
        }
        for cliente in Cliente.objects.filter(activo=True).order_by('nombre')
    ]
    metodos_pago = [
        {
            'id': metodo.id,
            'nombre': metodo.nombre,
            'tipo': metodo.tipo,
        }
        for metodo in MetodoPago.objects.filter(activo=True).order_by('nombre')
    ]
    sesiones_caja = [
        {
            'id': sesion.id,
            'caja': sesion.caja.nombre,
            'cajero': sesion.cajero.get_username(),
        }
        for sesion in SesionCaja.objects.select_related('caja', 'cajero').filter(
            estado=SesionCaja.Estado.ABIERTA,
        )
    ]

    return render(
        request,
        'retail/pos.html',
        {
            'productos': productos,
            'clientes': clientes,
            'metodos_pago': metodos_pago,
            'sesiones_caja': sesiones_caja,
        },
    )


@login_required
@require_POST
def crear_venta_pos_view(request):
    try:
        datos = json.loads(request.body.decode('utf-8'))
        venta = crear_venta_pos(request.user, datos)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'La solicitud no tiene un JSON valido.'}, status=400)
    except ObjectDoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Uno de los datos seleccionados ya no existe.'}, status=400)
    except ValidationError as error:
        return JsonResponse({'ok': False, 'error': _mensaje_validacion(error)}, status=400)

    return JsonResponse(
        {
            'ok': True,
            'venta': {
                'id': venta.id,
                'numero': venta.numero,
                'total': str(venta.total),
                'admin_url': f'/admin/retail/venta/{venta.id}/change/',
            },
        },
        status=201,
    )


def _mensaje_validacion(error):
    if hasattr(error, 'message_dict'):
        mensajes = []
        for valores in error.message_dict.values():
            mensajes.extend(valores)
        return ' '.join(mensajes)
    return ' '.join(error.messages)
