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
    path("checkout/opciones/", views.checkout_opciones, name="checkout_opciones"),
    path("checkout/procesar/", views.checkout_procesar, name="checkout_procesar"),
    path("checkout/success/", views.checkout_success, name="checkout_success"),
]
