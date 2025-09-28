from django.contrib import admin
from .models import Itinerario, Paquete, Foto, Salida, Usuario, Carrito, CarritoItem, Incluye, NoIncluye, Recomendaciones, Compra, CompraItem, InformacionCompra

admin.site.register(Usuario)

class CompraItemInline(admin.TabularInline):
    model = CompraItem
    extra = 0
    readonly_fields = ("paquete", "salida", "cantidad", "precio_unitario")

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "total", "estado", "medio_pago", "opcion_pais", "fecha")
    list_filter = ("estado", "medio_pago", "opcion_pais", "fecha")
    search_fields = ("usuario__email", "referencia_externa")
    readonly_fields = ("fecha",)
    inlines = [CompraItemInline]

class CarritoItemInline(admin.TabularInline):
    model = CarritoItem
    extra = 1

@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    inlines = [CarritoItemInline]

class ItinerarioInline(admin.TabularInline):
    model = Itinerario
    extra = 1

class FotoInline(admin.TabularInline):
    model = Foto
    extra = 1

class SalidaInline(admin.TabularInline):
    model = Salida
    extra = 1

class IncluyeInline(admin.TabularInline):
    model = Incluye
    extra = 1

class NoIncluyeInline(admin.TabularInline):
    model = NoIncluye
    extra = 1

class RecomendacionesInline(admin.TabularInline):
    model = Recomendaciones
    extra = 1

@admin.register(Paquete)
class PaqueteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ciudad', 'precio', 'duracion_horas', 'fecha_creacion')
    list_filter = ('ciudad',)
    search_fields = ('nombre', 'descripcion')
    inlines = [FotoInline, SalidaInline, ItinerarioInline, IncluyeInline, NoIncluyeInline, RecomendacionesInline]

@admin.register(Foto)
class FotoAdmin(admin.ModelAdmin):
    list_display = ('paquete', 'descripcion')
    search_fields = ('descripcion', 'paquete__nombre')

@admin.register(Salida)
class SalidaAdmin(admin.ModelAdmin):
    list_display = ('paquete', 'fecha')
    list_filter = ('fecha',)
    search_fields = ('paquete__nombre',)

class InformacionCompraInline(admin.StackedInline):  # o TabularInline
    model = InformacionCompra
    can_delete = False
    extra = 0

class CompraAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "total", "estado", "medio_pago", "opcion_pais", "fecha")
    list_filter = ("estado", "medio_pago", "opcion_pais", "fecha")
    search_fields = ("usuario__email", "referencia_externa")
    readonly_fields = ("fecha",)
    inlines = [CompraItemInline, InformacionCompraInline]  # añadís aquí el inline

@admin.register(InformacionCompra)
class InformacionCompraAdmin(admin.ModelAdmin):
    list_display = ("compra", "nombre", "pais", "ciudad", "codigo_postal")
    search_fields = ("compra__usuario__email", "pais", "ciudad")