from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class Usuario(AbstractUser):
    direccion = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"
    
class Carrito(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='carrito')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carrito de {self.usuario.username}"

class Paquete(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen_portada = models.ImageField(upload_to='paquetes/portadas/')
    imagen_perfil = models.ImageField(upload_to='paquetes/perfil/')
    duracion_horas = models.PositiveIntegerField()
    ciudad = models.CharField(max_length=100)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre
    
class Incluye(models.Model):
    paquete = models.ForeignKey(Paquete, related_name="incluye", on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)

    def __str__(self):
        return self.nombre


class NoIncluye(models.Model):
    paquete = models.ForeignKey(Paquete, related_name="no_incluye", on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)

    def __str__(self):
        return self.nombre

class Recomendaciones(models.Model):
    paquete = models.ForeignKey(Paquete, related_name="recomendaciones", on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)

    def __str__(self):
        return self.nombre

class Itinerario(models.Model):
    paquete = models.ForeignKey(Paquete, related_name="itinerarios", on_delete=models.CASCADE)
    orden = models.PositiveIntegerField()
    nombre = models.CharField(max_length=200)

    class Meta:
        ordering = ["orden"]

    def __str__(self):
        return f"{self.orden}. {self.nombre}"

class Foto(models.Model):
    paquete = models.ForeignKey(Paquete, related_name='fotos', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='paquetes/fotos/')
    descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Foto de {self.paquete.nombre}"

class Salida(models.Model):
    paquete = models.ForeignKey(Paquete, related_name='salidas', on_delete=models.CASCADE)
    fecha = models.DateField()

    def __str__(self):
        return f"{self.paquete.nombre} - {self.fecha}"

class CarritoItem(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    paquete = models.ForeignKey(Paquete, on_delete=models.CASCADE)
    # NUEVO: salida elegida para este ítem (opcional si el paquete no tiene salidas)
    salida = models.ForeignKey(Salida, on_delete=models.PROTECT, null=True, blank=True, related_name='items')
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        # ahora la unicidad distingue por salida
        unique_together = ('carrito', 'paquete', 'salida')

    def __str__(self):
        if self.salida_id:
            return f"{self.paquete.nombre} ({self.salida.fecha}) x{self.cantidad} en carrito de {self.carrito.usuario.username}"
        return f"{self.paquete.nombre} x{self.cantidad} en carrito de {self.carrito.usuario.username}"


class Compra(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("aprobado", "Aprobado"),
        ("fallido", "Fallido"),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="compras")
    total = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    email = models.EmailField(blank=True, null=True)


    medio_pago = models.CharField(
        max_length=30,
        choices=[
            ("stripe", "Stripe"),
            ("transferencia_arg", "Transferencia Argentina"),
            ("transferencia_br", "Transferencia Brasil"),
        ],
    )

    opcion_pais = models.CharField(
        max_length=20,
        choices=[
            ("argentina", "Argentina"),
            ("brasil", "Brasil"),
            ("mundo", "Resto del mundo"),
        ],
    )

    referencia_externa = models.CharField(max_length=255, blank=True, null=True)  # id de Stripe, nro comprobante, etc.

    def __str__(self):
        return f"Compra {self.id} - {self.usuario.email} - {self.total} ({self.estado})"

class CompraItem(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="items")
    paquete = models.ForeignKey("Paquete", on_delete=models.SET_NULL, null=True)
    salida = models.ForeignKey("Salida", on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.paquete} x{self.cantidad}"
