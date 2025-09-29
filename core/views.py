from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import localdate
from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from decimal import Decimal
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from .models import Carrito, CarritoItem, Paquete, Compra, CompraItem, InformacionCompra
from django.urls import reverse
from .models import Paquete, Salida, Carrito, CarritoItem
from django.db.models import Q
from django.utils.timezone import localdate
from django.conf import settings
import stripe
from core.utils.codigos_iso import CODIGOS_ISO
from django.core.mail import send_mail


def paquete(request, pk):
    p = get_object_or_404(Paquete, pk=pk)
    salidas = p.salidas.filter(fecha__gte=localdate()).order_by('fecha')

    # 6 paquetes aleatorios distintos al actual
    similares = Paquete.objects.exclude(pk=p.pk).order_by('?')[:6]

    if request.method == "POST":
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        if not request.user.is_authenticated:
            if is_ajax:
                return JsonResponse({'require_login': True}, status=401)
            return render(request, "paquete.html", {
                "paquete": p, "salidas": salidas, "require_login": True, "similares": similares
            })

        salida_obj = None
        salida_id = request.POST.get("salida_id")
        if salidas.exists():
            try:
                salida_obj = salidas.get(id=salida_id)
            except Salida.DoesNotExist:
                if is_ajax:
                    return JsonResponse({'ok': False, 'error': 'Salida inválida.'}, status=400)
                return render(request, "paquete.html", {
                    "paquete": p, "salidas": salidas, "similares": similares
                })

        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        item, created = CarritoItem.objects.get_or_create(
            carrito=carrito,
            paquete=p,
            salida=salida_obj,
            defaults={"cantidad": 1},
        )
        if not created:
            item.cantidad = F('cantidad') + 1
            item.save(update_fields=['cantidad'])
            item.refresh_from_db()

        if is_ajax:
            return JsonResponse({'ok': True})
        return redirect("carrito")

    return render(request, "paquete.html", {
        "paquete": p,
        "salidas": salidas,
        "similares": similares
    })



# helper para totales
def _totales_carrito(carrito):
    qs = carrito.items.select_related('paquete')
    subtotal = qs.aggregate(
        s=Sum(ExpressionWrapper(F('cantidad') * F('paquete__precio'),
                                output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['s'] or Decimal('0')
    productos = qs.count()  # productos distintos
    unidades = qs.aggregate(u=Sum('cantidad'))['u'] or 0
    return subtotal, productos, unidades

@login_required
def carrito(request):
    carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
    qs = (carrito.items
          .select_related('paquete', 'salida')
          .annotate(item_total=ExpressionWrapper(
              F('cantidad') * F('paquete__precio'),
              output_field=DecimalField(max_digits=12, decimal_places=2)
          )))
    items = list(qs)
    subtotal = sum((i.item_total for i in items), Decimal('0'))
    productos = carrito.items.count()
    unidades = sum(i.cantidad for i in items)

    return render(request, "carrito.html", {
        "items": items,
        "totales": {"subtotal": subtotal, "productos": productos, "unidades": unidades},
    })


@login_required
def carrito_item_update(request, item_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    action = request.POST.get("action")  # "inc" | "dec" | "remove"
    if action not in ("inc", "dec", "remove"):
        return HttpResponseBadRequest("invalid action")

    item = get_object_or_404(
        CarritoItem.objects.select_related("carrito", "paquete"),
        id=item_id, carrito__usuario=request.user
    )
    carrito = item.carrito
    removed = False

    if action == "inc":
        item.cantidad = F("cantidad") + 1
        item.save(update_fields=["cantidad"])
        item.refresh_from_db()
    elif action == "dec":
        item.cantidad = F("cantidad") - 1
        item.save(update_fields=["cantidad"])
        item.refresh_from_db()
        if item.cantidad <= 0:
            removed = True
            item.delete()
    else:  # remove
        removed = True
        item.delete()

    subtotal, productos, unidades = _totales_carrito(carrito)

    payload = {
        "removed": removed,
        "item_id": item_id,
        "subtotal": float(subtotal),
        "productos": productos,
        "unidades": int(unidades),
    }

    if not removed:
        payload.update({
            "cantidad": int(item.cantidad),
            "item_total": float(item.cantidad * item.paquete.precio),
            "unit_price": float(item.paquete.precio),
        })

    return JsonResponse(payload)

def index(request):
    paquetes = Paquete.objects.all()
    return render(request, "index.html", {"paquetes": paquetes})

def contacto(request):
    return render(request, "contacto.html")

def faq(request):
    return render(request, "faq.html")

@login_required
def mis_compras(request):
    compras = Compra.objects.filter(usuario=request.user).order_by('-fecha')  # ejemplo
    return render(request, "mis_compras.html", {"compras": compras})

def politicas(request):
    return render(request, "politicas.html")



# configurando metodos de pago
from core.utils.codigos_iso import CODIGOS_ISO  # al inicio de views.py

from decimal import Decimal
from django.db.models import F, ExpressionWrapper, DecimalField
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
import stripe

from decimal import Decimal
from django.db.models import F, ExpressionWrapper, DecimalField
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
import stripe

@login_required
def pago_opciones(request):
    carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
    qs = (
        carrito.items
        .select_related('paquete')
        .annotate(item_total=ExpressionWrapper(
            F('cantidad') * F('paquete__precio'),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        ))
    )
    subtotal = sum((i.item_total for i in qs), Decimal('0'))

    if request.method == 'POST':
        pais = request.POST.get('pais')            # argentina/brasil/mundo
        medio = request.POST.get('medio_pago')
        pais_mundo = request.POST.get('pais_mundo')  # país dentro de resto del mundo

        # guardás en la sesión la opción elegida (para Stripe)
        request.session['opcion_pais'] = pais
        request.session['pais_mundo'] = pais_mundo

                # ---------- Transferencia ----------
        if medio == 'transferencia':
            if pais not in ['argentina', 'brasil']:
                return JsonResponse({"error": "Transferencia no disponible"}, status=400)

            # crear la compra
            compra = Compra.objects.create(
                usuario=request.user,
                email=request.user.email,
                total=subtotal,
                estado="pendiente",  # hasta que vos la confirmes
                medio_pago=f"transferencia_{pais}",
                opcion_pais=pais,
            )

            # crear items de la compra
            for it in qs:
                CompraItem.objects.create(
                    compra=compra,
                    paquete=it.paquete,
                    salida=it.salida,
                    cantidad=it.cantidad,
                    precio_unitario=it.paquete.precio,
                )

            # crear información de envío
            InformacionCompra.objects.create(
                compra=compra,
                nombre=request.POST.get("nombre"),
                direccion_linea1=request.POST.get("direccion"),
                ciudad=request.POST.get("ciudad"),
                codigo_postal=request.POST.get("codigo_postal"),
                pais=pais.title()
            )

            carrito.items.all().delete()
            
            nombre = request.POST.get("nombre")
            cbu = "1234567890123456789012"  # o el que generes dinámicamente

            html = f"""
                <h1>Hola {nombre}</h1>
                <p>¡Gracias por elegirnos!</p>
                <p>Para completar tu reserva te compartimos nuestro <strong>CBU: {cbu}</strong>.</p>
                <p>Por favor realizá la transferencia y envianos el comprobante a 
                <strong>excursionesbrasil@gmail.com</strong> o por WhatsApp al 
                <strong>3534-136384</strong>.</p>
                <p>Es necesario que en el <strong>asunto</strong> o <strong>motivo</strong> del mensaje aclares <em>(Comprobante de transferencia)</em> para facilitar y agilizar los tiempos de verificación.</p>
                <p>Recordá que disponés de <strong>72 horas</strong> para enviarnos el comprobante; pasado ese plazo la orden se cancelará automáticamente.</p>
                <p><strong>Este es un mensaje automático</strong>, no es necesario que lo respondas.</p>
                <p><strong>Saludos cordiales,</strong><br>El equipo de Excursiones Brasil</p>
                """

            send_mail(
                subject='Instrucciones para tu pago',
                message='Versión texto plano del mensaje…',  # fallback
                from_email='empleosvm518@gmail.com',
                recipient_list=[request.user.email],
                html_message=html
            )

            # devolver un HttpResponse con instrucciones de transferencia
            return HttpResponse(
                f"Gracias por tu compra #{compra.id}. "
                "Para completar el pago realiza una transferencia a la cuenta bancaria indicada. "
                "Recibirás un email con los datos de la transferencia."
            )


        # ---------- Stripe ----------
        if medio == 'stripe':
            stripe.api_key = settings.STRIPE_SECRET_KEY

            if pais == 'argentina':
                allowed_countries = ['AR']
            elif pais == 'brasil':
                allowed_countries = ['BR']
            elif pais == 'mundo' and pais_mundo:
                clave = pais_mundo.strip().lower()
                allowed_countries = [CODIGOS_ISO.get(clave, 'US')]
            else:
                allowed_countries = None

            line_items = [{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': int(it.paquete.precio * 100),
                    'product_data': {'name': it.paquete.nombre},
                },
                'quantity': it.cantidad,
            } for it in qs]

            kwargs = dict(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=request.build_absolute_uri(
                    reverse('pago_exitoso')
                ) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri(reverse('carrito')),
                customer_email=request.user.email,
            )
            if allowed_countries:
                kwargs['shipping_address_collection'] = {
                    'allowed_countries': allowed_countries
                }

            checkout_session = stripe.checkout.Session.create(**kwargs)
            return redirect(checkout_session.url)

    return render(request, "pago_opciones.html", {"subtotal": subtotal})




@login_required
def pago_exitoso(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return HttpResponse("Falta session_id", status=400)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    session = stripe.checkout.Session.retrieve(
        session_id,
        expand=['customer_details', 'shipping']
    )

    # datos del cliente / envío desde Stripe
    customer_details = session.get('customer_details') or {}
    shipping = session.get('shipping') or {}

    name = customer_details.get('name') or shipping.get('name')
    address = customer_details.get('address') or shipping.get('address') or {}

    line1 = address.get('line1')
    line2 = address.get('line2')
    city = address.get('city')
    country_iso = address.get('country')
    postal = address.get('postal_code')

    # traducir código ISO a nombre
    nombre_pais = None
    if country_iso:
        for k, v in CODIGOS_ISO.items():
            if v.upper() == country_iso.upper():
                nombre_pais = k.title()
                break
    if not nombre_pais:
        nombre_pais = country_iso  # fallback si no lo encuentra

    # recuperar del session qué opción había elegido
    opcion_pais = request.session.pop('opcion_pais', 'mundo')
    pais_mundo = request.session.pop('pais_mundo', None)
    carrito = request.user.carrito
    items = list(carrito.items.select_related('paquete'))
    subtotal = sum(Decimal(it.paquete.precio) * it.cantidad for it in items)

    # crear la compra
    compra = Compra.objects.create(
        usuario=request.user,
        email=request.user.email,
        total=subtotal,
        estado="aprobado",
        medio_pago="stripe",
        opcion_pais=opcion_pais,  # ahora guarda la opción real
        referencia_externa=session.id,
    )

    # crear la información de envío asociada
    InformacionCompra.objects.create(
        compra=compra,
        nombre=name,
        direccion_linea1=line1,
        direccion_linea2=line2,
        ciudad=city,
        pais=nombre_pais,  # nombre del país en vez del ISO
        codigo_postal=postal,
    )

    # crear los items
    for it in items:
        CompraItem.objects.create(
            compra=compra,
            paquete=it.paquete,
            salida=it.salida,
            cantidad=it.cantidad,
            precio_unitario=it.paquete.precio,
        )

    carrito.items.all().delete()

    return HttpResponse("Pago realizado con éxito. ¡Gracias por tu compra!")