MarketApi
=========

MarketApi es una API muy simple para usar con el sistema MarketPlace de MercadoPago.

Esta API pretende ser útil en escenarios no muy complejos, y tiene como fin ser lo más
transparente posible al momento de interactuar con MercadoPago.

Si aún no tenes una APP creada en mercadolibre podes ingresar a https://applications.mercadolibre.com.ar/list
y crear la tuya, es un paso necesario para obtener el `client_id` y `client_secret`.

Nota: Por convención use App ID cómo `client_id` y Secret Key cómo `client_secret`

Ejemplo de uso:

```python
CLIENT_ID = 123456 # client_id de tu APP
CLIENT_SECRET = "XZY123" # client_secret de tu APP
REDIRECT_URI = "http://127.0.0.1:8000/registrar_mercadopago/" # debe ser la misma URI que registraste en tu APP

# Instancia la API y crea el link de autorización
mktapi = MarketApi(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
code_link = mktapi.get_client_code_link()
print code_link

'https://auth.mercadolibre.com.ar/authorization?client_id=...&response_type=code&platform_id=mp&redirect_uri=http://127.0.0.1:8000/registrar_mercadopago/'

# En la dirección de retorno (redirect_uri) por GET llega el `code`, con éste creamos el `access_token`
code = "TG-1234567890abcdef"
token = mktapi.get_seller_access_token(code)
print token

{u'access_token': u'APP_USR-.....__F_G__-123456',
u'expires_in': 21600,
u'refresh_token': u'TG-1234567890abcdef',
u'scope': u'offline_access read write',
u'token_type': u'bearer'}

# El primer token expira en el primer uso (según la doc), por eso lo mejor es refrescar el token para crear 
# uno mas duradero.
# El token expira en 6hs (60*60*6 = 21600) pero puede refrescarse para no tener que volver a pedir autorización
mktapi.refresh_seller_access_token()

# Creamos la instancia del preference
preferences = MarketPreferences()

# Cargamos el primer producto
item = MarketItem(123, "Bici loca para vos que sos un hipster", "Con esta bici vas a ser el mas zarpado de tus amigos hipsters!", 2500.00, "https://farm2.staticflickr.com/1105/631945084_c9930a4fb0_o.jpg")

# Asociamos al preference
preferences.set_item(item)
# o una lista de varios items
# preferences.set_items([item1, item2, item3, ...]) # una lista de items

mktapi.set_buy_preferences(preference)

# retorna el preference que nos devuelve MercadoPago
# {.......}

print mktapi.get_sandbox_init_point()
>>> https://sandbox.mercadopago.com/mla/checkout/pay?pref_id=......
```
