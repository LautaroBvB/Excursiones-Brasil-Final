from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import localdate
from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from decimal import Decimal
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from .models import Carrito, CarritoItem, Paquete, Compra, CompraItem
from django.urls import reverse
from .models import Paquete, Salida, Carrito, CarritoItem
from django.db.models import Q
from django.utils.timezone import localdate
from django.conf import settings
import stripe

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

    # flag para permitir acceso a checkout_opciones
    request.session['from_cart'] = True

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

def mis_compras(request):
    return render(request, "mis_compras.html")

def politicas(request):
    return render(request, "politicas.html")



# Prueba
@login_required
def checkout_opciones(request):
    if not request.session.pop('from_cart', False):
        return JsonResponse({"error": "Acceso inválido"}, status=400)

    carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
    subtotal, _, _ = _totales_carrito(carrito)
    return render(request, "checkout_opciones.html", {"subtotal": subtotal})



@login_required
def checkout_procesar(request):
    pais = request.POST.get("pais")
    medio = request.POST.get("medio_pago")

    carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
    subtotal, _, _ = _totales_carrito(carrito)

    # ---------- Transferencia ----------
    if medio == "transferencia":
        if pais not in ["argentina", "brasil"]:
            return JsonResponse({"error": "Transferencia no disponible"}, status=400)

        compra = Compra.objects.create(
            usuario=request.user,
            email=request.user.email,
            total=subtotal * Decimal("0.85"),  # aplica el 15% desc
            medio_pago=f"transferencia_{pais}",
            estado="pendiente",
            opcion_pais=pais,
        )

        # copiar ítems
        for item in carrito.items.all():
            CompraItem.objects.create(
                compra=compra,
                paquete=item.paquete,
                salida=item.salida,
                cantidad=item.cantidad,
                precio_unitario=item.paquete.precio,
            )
        carrito.delete()

    # ---------- Stripe ----------
    compra = Compra.objects.create(
        usuario=request.user,
        email=request.user.email,
        total=subtotal,
        medio_pago="stripe",
        estado="pendiente",
        opcion_pais=pais,
    )
    for item in carrito.items.all():
        CompraItem.objects.create(
            compra=compra,
            paquete=item.paquete,
            salida=item.salida,
            cantidad=item.cantidad,
            precio_unitario=item.paquete.precio,
        )

    session = stripe.checkout.Session.create(
        customer_email=request.user.email,
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": "Excursiones Brasil"},
                "unit_amount": int(subtotal * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.build_absolute_uri(
            reverse("checkout_success") + f"?compra_id={compra.id}"
        ),
        cancel_url=request.build_absolute_uri(reverse("checkout_opciones")),
    )

    compra.referencia_externa = session.id
    compra.save()

    return redirect(session.url, code=303)


# Esta función realiza los movimientos posteriores a la compra exitosa
@login_required
def checkout_success(request):
    compra_id = request.GET.get("compra_id")
    compra = Compra.objects.filter(id=compra_id, usuario=request.user).first()
    if not compra:
        return HttpResponse("Compra no encontrada", status=404)

    compra.estado = "aprobado"
    compra.save()

    # limpiar carrito (si aún existe)
    Carrito.objects.filter(usuario=request.user).delete()

    return HttpResponse("Pago realizado con éxito ✅")