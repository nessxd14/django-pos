from django.contrib import admin

from .models import (
    Caja,
    Categoria,
    Cliente,
    DetalleVenta,
    MetodoPago,
    MovimientoInventario,
    Pago,
    PerfilEmpleado,
    Producto,
    Proveedor,
    SesionCaja,
    Venta,
)


admin.site.site_header = 'Administracion Retail'
admin.site.site_title = 'Retail'
admin.site.index_title = 'Gestion de tienda'


@admin.register(PerfilEmpleado)
class PerfilEmpleadoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'telefono', 'activo')
    list_filter = ('rol', 'activo')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'telefono')


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activa', 'actualizado_en')
    list_filter = ('activa',)
    search_fields = ('nombre',)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nit', 'telefono', 'email', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'nit', 'telefono', 'email')


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        'sku',
        'nombre',
        'categoria',
        'precio_venta',
        'precio_mayorista',
        'stock_actual',
        'stock_minimo',
        'requiere_reposicion',
        'activo',
    )
    list_filter = ('activo', 'categoria', 'proveedor')
    search_fields = ('sku', 'codigo_barra', 'nombre')
    autocomplete_fields = ('categoria', 'proveedor')


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'nit_ci', 'telefono', 'email', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('nombre', 'nit_ci', 'telefono', 'email')


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ubicacion', 'activa')
    list_filter = ('activa',)
    search_fields = ('nombre', 'ubicacion')


@admin.register(SesionCaja)
class SesionCajaAdmin(admin.ModelAdmin):
    list_display = ('caja', 'cajero', 'estado', 'abierta_en', 'cerrada_en', 'monto_inicial', 'monto_cierre')
    list_filter = ('estado', 'caja')
    search_fields = ('caja__nombre', 'cajero__username')
    autocomplete_fields = ('caja', 'cajero')


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1
    autocomplete_fields = ('producto',)


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    autocomplete_fields = ('metodo_pago', 'sesion_caja', 'recibido_por')


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    inlines = (DetalleVentaInline, PagoInline)
    list_display = ('numero', 'fecha', 'canal', 'estado', 'cliente', 'vendedor', 'cajero', 'total')
    list_filter = ('canal', 'estado', 'fecha')
    search_fields = ('numero', 'cliente__nombre', 'vendedor__username', 'cajero__username')
    autocomplete_fields = ('cliente', 'vendedor', 'cajero', 'sesion_caja')


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ('venta', 'producto', 'cantidad', 'precio_unitario', 'descuento', 'total_linea')
    search_fields = ('venta__numero', 'producto__sku', 'producto__nombre')
    autocomplete_fields = ('venta', 'producto')


@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('nombre',)


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('venta', 'metodo_pago', 'monto', 'recibido_por', 'fecha')
    list_filter = ('metodo_pago', 'fecha')
    search_fields = ('venta__numero', 'referencia', 'recibido_por__username')
    autocomplete_fields = ('venta', 'sesion_caja', 'metodo_pago', 'recibido_por')


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tipo', 'cantidad', 'referencia', 'realizado_por', 'fecha')
    list_filter = ('tipo', 'fecha')
    search_fields = ('producto__sku', 'producto__nombre', 'referencia', 'realizado_por__username')
    autocomplete_fields = ('producto', 'venta', 'realizado_por')
