(function () {
    const form = document.getElementById('add-to-cart-form');
    if (!form) return;

    function getCookie(name) {
        const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return m ? m.pop() : '';
    }

    const googleLogin = "{% provider_login_url 'google' %}?next={{ request.path|urlencode }}";
    const cartUrl = "{% url 'carrito' %}"; // ← para el botón "Ir al carrito"

    async function submitAddToCart(e) {
        e.preventDefault();

        const fd = new FormData(form);
        try {
            const res = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: fd,
            });

            if (res.status === 401) {
                // no logueado → modal de login
                Swal.fire({
                    html: `
                            <h3>{% trans "Inicia sesión con sólo un click" %}</h3>
                            <p>{% trans "Para agregar productos al carrito debes iniciar sesión o registrarte, ¡te toma segundos!" %}</p>
                            <ul class="icons" style="display:flex; gap:18px; justify-content:center; list-style:none; padding:0; margin:22px 0;">
                                <li><a href="${googleLogin}" class="icon brands fa-google"><span class="label">Google</span></a></li>
                                <li><a href="#" class="icon brands fa-apple"><span class="label">Apple</span></a></li>
                                <li><a href="#" class="icon brands fa-facebook"><span class="label">Facebook</span></a></li>
                                <li><a href="#" class="icon brands fa-twitter"><span class="label">Twitter</span></a></li>
                            </ul>
                            `,
                    showConfirmButton: false,
                    showCancelButton: true,
                    cancelButtonText: '{% trans "Cancelar" %}',
                    buttonsStyling: false,
                    customClass: { cancelButton: 'button' },
                });
                return;
            }

            const data = await res.json();

            if (data.ok) {
                // éxito → mostrar SweetAlert con opción de ir al carrito
                Swal.fire({
                    icon: 'success',
                    title: '{% trans "¡Agregado al carrito!" %}',
                    text: '{% trans "El paquete fue agregado exitosamente." %}',
                    showCancelButton: true,
                    confirmButtonText: '{% trans "Ir al carrito" %}',
                    cancelButtonText: '{% trans "Seguir explorando" %}',
                    reverseButtons: true,
                    buttonsStyling: false,
                    customClass: {
                        confirmButton: 'button primary',
                        cancelButton: 'button'
                    }
                }).then(r => { if (r.isConfirmed) window.location = cartUrl; });
                return;
            }

            // error controlado
            Swal.fire({
                icon: 'error',
                title: '{% trans "Ups" %}',
                text: data.error || '{% trans "No pudimos agregar el paquete." %}'
            });

        } catch (err) {
            console.error(err);
            Swal.fire({
                icon: 'error',
                title: '{% trans "Ups" %}',
                text: '{% trans "Error de red. Intentalo nuevamente." %}'
            });
        }
    }

    form.addEventListener('submit', submitAddToCart);
})();