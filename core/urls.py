from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="inicio"),
    path("paquete/<int:pk>/", views.paquete, name="paquete"),
    path("carrito/", views.carrito, name="carrito"),
    path("carrito/item/<int:item_id>/update/", views.carrito_item_update, name="carrito_item_update"),
    path("contacto/", views.contacto, name="contacto"),
    path("preguntas_frecuentes/", views.faq, name="faq"),
    path("mis_compras/", views.mis_compras, name="mis_compras"),
    path("politicas/", views.politicas, name="politicas"),
    path("opciones_de_pago", views.pago_opciones, name="opciones_de_pago"),
    path("pago_exitoso/", views.pago_exitoso, name="pago_exitoso"),
]
