from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Carrito

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_carrito_automatico(sender, instance, created, **kwargs):
    if created:
        Carrito.objects.get_or_create(usuario=instance)