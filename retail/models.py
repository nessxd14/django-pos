from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class TimeStampedModel(models.Model):
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PerfilEmpleado(TimeStampedModel):
    class Rol(models.TextChoices):
        ALMACEN = 'almacen', 'Almacen'
        MAYORISTA = 'mayorista', 'Mayorista'
        VENDEDOR = 'vendedor', 'Vendedor'
        CAJA = 'caja', 'Caja'
        ADMINISTRACION = 'administracion', 'Administracion'

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_retail',
    )
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.VENDEDOR)
    telefono = models.CharField(max_length=30, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'perfil de empleado'
        verbose_name_plural = 'perfiles de empleados'

    def __str__(self):
        return f'{self.usuario.get_username()} - {self.get_rol_display()}'


class Categoria(TimeStampedModel):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'categoria'
        verbose_name_plural = 'categorias'

    def __str__(self):
        return self.nombre


class Proveedor(TimeStampedModel):
    nombre = models.CharField(max_length=160, unique=True)
    nit = models.CharField(max_length=40, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'proveedor'
        verbose_name_plural = 'proveedores'

    def __str__(self):
        return self.nombre


class Producto(TimeStampedModel):
    sku = models.CharField('SKU', max_length=40, unique=True)
    codigo_barra = models.CharField(max_length=80, unique=True, blank=True, null=True)
    nombre = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='productos',
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name='productos',
        blank=True,
        null=True,
    )
    precio_compra = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    precio_venta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    precio_mayorista = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    stock_actual = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['nombre']),
        ]
        verbose_name = 'producto'
        verbose_name_plural = 'productos'

    @property
    def requiere_reposicion(self):
        return self.stock_actual <= self.stock_minimo

    def precio_para_canal(self, canal):
        if canal == Venta.Canal.MAYORISTA and self.precio_mayorista:
            return self.precio_mayorista
        return self.precio_venta

    def __str__(self):
        return f'{self.sku} - {self.nombre}'


class Cliente(TimeStampedModel):
    class Tipo(models.TextChoices):
        MINORISTA = 'minorista', 'Minorista'
        MAYORISTA = 'mayorista', 'Mayorista'
        INSTITUCION = 'institucion', 'Institucion'

    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.MINORISTA)
    nombre = models.CharField(max_length=180)
    nit_ci = models.CharField('NIT/CI', max_length=40, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    limite_credito = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'cliente'
        verbose_name_plural = 'clientes'

    def __str__(self):
        return f'{self.nombre} ({self.get_tipo_display()})'


class Caja(TimeStampedModel):
    nombre = models.CharField(max_length=80, unique=True)
    ubicacion = models.CharField(max_length=120, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'caja'
        verbose_name_plural = 'cajas'

    def __str__(self):
        return self.nombre


class SesionCaja(TimeStampedModel):
    class Estado(models.TextChoices):
        ABIERTA = 'abierta', 'Abierta'
        CERRADA = 'cerrada', 'Cerrada'

    caja = models.ForeignKey(Caja, on_delete=models.PROTECT, related_name='sesiones')
    cajero = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sesiones_caja',
    )
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)
    abierta_en = models.DateTimeField(default=timezone.now)
    cerrada_en = models.DateTimeField(blank=True, null=True)
    monto_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    monto_cierre = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    notas = models.TextField(blank=True)

    class Meta:
        ordering = ['-abierta_en']
        constraints = [
            models.UniqueConstraint(
                fields=['caja'],
                condition=Q(estado='abierta'),
                name='una_sesion_abierta_por_caja',
            ),
        ]
        verbose_name = 'sesion de caja'
        verbose_name_plural = 'sesiones de caja'

    def cerrar(self, monto_cierre):
        self.estado = self.Estado.CERRADA
        self.cerrada_en = timezone.now()
        self.monto_cierre = monto_cierre
        self.save(update_fields=['estado', 'cerrada_en', 'monto_cierre', 'actualizado_en'])

    def __str__(self):
        return f'{self.caja} - {self.get_estado_display()}'


class Venta(TimeStampedModel):
    class Canal(models.TextChoices):
        MOSTRADOR = 'mostrador', 'Mostrador'
        MAYORISTA = 'mayorista', 'Mayorista'

    class Estado(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        PAGADA = 'pagada', 'Pagada'
        ANULADA = 'anulada', 'Anulada'

    numero = models.CharField(max_length=30, unique=True)
    canal = models.CharField(max_length=20, choices=Canal.choices, default=Canal.MOSTRADOR)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='ventas',
        blank=True,
        null=True,
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ventas_realizadas',
    )
    cajero = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ventas_cobradas',
        blank=True,
        null=True,
    )
    sesion_caja = models.ForeignKey(
        SesionCaja,
        on_delete=models.PROTECT,
        related_name='ventas',
        blank=True,
        null=True,
    )
    fecha = models.DateTimeField(default=timezone.now)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    notas = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['numero']),
            models.Index(fields=['fecha']),
            models.Index(fields=['estado']),
        ]
        verbose_name = 'venta'
        verbose_name_plural = 'ventas'

    def recalcular_totales(self):
        subtotal = self.detalles.aggregate(total=models.Sum('total_linea'))['total'] or Decimal('0.00')
        self.subtotal = subtotal
        self.total = max(Decimal('0.00'), subtotal - self.descuento)
        self.save(update_fields=['subtotal', 'total', 'actualizado_en'])

    def __str__(self):
        return self.numero


class DetalleVenta(TimeStampedModel):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='detalles_venta')
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_linea = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = 'detalle de venta'
        verbose_name_plural = 'detalles de venta'

    def save(self, *args, **kwargs):
        if not self.precio_unitario:
            self.precio_unitario = self.producto.precio_para_canal(self.venta.canal)
        self.total_linea = max(
            Decimal('0.00'),
            (self.precio_unitario * self.cantidad) - self.descuento,
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.producto} x {self.cantidad}'


class MetodoPago(TimeStampedModel):
    class Tipo(models.TextChoices):
        EFECTIVO = 'efectivo', 'Efectivo'
        QR = 'qr', 'QR'
        TARJETA = 'tarjeta', 'Tarjeta'
        TRANSFERENCIA = 'transferencia', 'Transferencia'
        CREDITO = 'credito', 'Credito'

    nombre = models.CharField(max_length=80, unique=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'metodo de pago'
        verbose_name_plural = 'metodos de pago'

    def __str__(self):
        return self.nombre


class Pago(TimeStampedModel):
    venta = models.ForeignKey(Venta, on_delete=models.PROTECT, related_name='pagos')
    sesion_caja = models.ForeignKey(
        SesionCaja,
        on_delete=models.PROTECT,
        related_name='pagos',
        blank=True,
        null=True,
    )
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT, related_name='pagos')
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    referencia = models.CharField(max_length=120, blank=True)
    recibido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='pagos_recibidos',
    )
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'pago'
        verbose_name_plural = 'pagos'

    def __str__(self):
        return f'{self.metodo_pago} - {self.monto}'


class MovimientoInventario(TimeStampedModel):
    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        SALIDA = 'salida', 'Salida'
        AJUSTE = 'ajuste', 'Ajuste'
        DEVOLUCION = 'devolucion', 'Devolucion'

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos')
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    referencia = models.CharField(max_length=120, blank=True)
    venta = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name='movimientos_inventario',
        blank=True,
        null=True,
    )
    realizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='movimientos_inventario',
    )
    fecha = models.DateTimeField(default=timezone.now)
    notas = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'movimiento de inventario'
        verbose_name_plural = 'movimientos de inventario'

    def __str__(self):
        return f'{self.get_tipo_display()} {self.cantidad} - {self.producto}'
