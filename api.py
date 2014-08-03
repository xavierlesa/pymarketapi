# -*- coding:utf-8 -*-
"""
MarketApi es una API muy simple para usar con el sistema MarketPlace de MercadoPago.

Esta API pretende ser útil en escenarios no muy complejos, y tiene como fin ser lo más
transparente posible al momento de interactuar con MercadoPago.

@author: Xavier Lesa <xavierlesa@gmail.com>
@repo: https://github.com/


Si aún no tenes una APP creada en mercadolibre podes ingresar a https://applications.mercadolibre.com.ar/list
y crear la tuya, es un paso necesario para obtener el `client_id` y `client_secret`.
Nota: Por convención use App ID cómo `client_id` y Secret Key cómo `client_secret`

Ejemplo de uso:

>>> CLIENT_ID = 123456 # client_id de tu APP
>>> CLIENT_SECRET = "XZY123" # client_secret de tu APP
>>> REDIRECT_URI = "http://127.0.0.1:8000/registrar_mercadopago/" # debe ser la misma URI que registraste en tu APP
>>> # Instancia la API y crea el link de autorización
>>> mkp = MarketApi(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
>>> code_link = mkp.get_client_code_link()
>>> print code_link
>>> 'https://auth.mercadolibre.com.ar/authorization?client_id=...&response_type=code&platform_id=mp&redirect_uri=http://127.0.0.1:8000/registrar_mercadopago/'
>>> # En la dirección de retorno (redirect_uri) por GET llega el `code`, con éste creamos el `access_token`
>>> code = "TG-1234567890abcdef"
>>> token = mkp.get_seller_access_token(code)
>>> print token
>>> {u'access_token': u'APP_USR-.....__F_G__-123456',
>>> u'expires_in': 21600,
>>> u'refresh_token': u'TG-1234567890abcdef',
>>> u'scope': u'offline_access read write',
>>> u'token_type': u'bearer'}
>>> # El primer token expira en el primer uso (según la doc), por eso lo mejor es refrescar el token para crear 
>>> # uno mas duradero.
>>> # El token expira en 6hs (60*60*6 = 21600) pero puede refrescarse para no tener que volver a pedir autorización
>>> mkt.refresh_seller_access_token()
"""

import datetime
import json
import requests

class MPException(Exception):
    def __init__(self, code):
        self.code = code
    def __str__(self):
        return repr(self.code)


URL_AUTH = 'https://api.mercadolibre.com/oauth/token'
URL_AUTHORIZATION = 'https://auth.mercadolibre.com.ar/authorization'
URL_PREFERENCES = 'https://api.mercadolibre.com/checkout/preferences'
CURRENCY_ID = 'ARS' # https://api.mercadolibre.com/currencies/
MARKETPLACE_FEE = float(5.00)


class MarketItem:
    """
    Clase abstracta para definir los atributos de un item/artículo/producto.

    """
    def __init__(self, id, title, description, unit_price, picture_url, quantity=1, currency_id=None, market_preferences=None):
        """
        Define los siguientes atributos:
        `id`: El ID del item/artículo/producto
        `title`: Nombre o título del producto
        `description`: Descripción detallada del producto
        `quantity`: Cantidades de éste productos, por defecto 1
        `unit_price`: Precio unitario del producto, debe ser un float
        `currency_id`: Moneda del producto, por defecto la moneda global CURRENCY_ID # ver https://api.mercadolibre.com/currencies/
        `picture_url`: La URL completa de la imagen del producto opcional

        """
        self.id = id
        self.title = title
        self.description = description
        self.quantity = quantity
        self.unit_price = unit_price
        self.currency_id = currency_id # https://api.mercadolibre.com/currencies/
        self.picture_url = picture_url
        self.market_preferences = market_preferences

    def get_title(self, *args, **kwargs):
        """
        Devuelve el título del producto.

        """
        return self.title

    def get_description(self, *args, **kwargs):
        """
        Devuelve la descripción del producto.

        """
        return self.description

    def get_quantity(self, *args, **kwargs):
        """
        Retorna la cantidad de productos.

        """
        return self.quantity

    def get_unit_price(self, *args, **kwargs):
        """
        Devuelve el precio unitario del producto, debe ser un float.

        """
        return self.unit_price

    def get_currency_id(self, *args, **kwargs):
        """
        Devuelve la moneda en la que está el producto.
        
        """
        return self.get_currency()

    def get_currency(self, *args, **kwargs):
        """
        Devuelve la moneda del producto.
        Si no tienen una moneda configurada intenta resolver la moneda del `preference`

        """
        if not self.currency_id and not self.market_preferences:
            raise MPException("El producto no tiene ninguna moneda configurada, debe setear `currency_id` en el producto o en el MarketPreferences")

        elif not self.currency_id and self.market_preferences:
            return self.market_preferences.get_currency()

        return self.currency_id

    def get_picture_url(self, *args, **kwargs):
        """
        Devuelve la URL completa de la imagen.
        ejemplo: https://farm2.staticflickr.com/1105/631945084_c9930a4fb0_o.jpg

        """
        return self.picture_url

    def get_json(self):
        """
        Devuelve el JSON del producto.

        """
        return {
            'id': self.id,
            'title': self.get_title(),
            'description': self.get_description(),
            'quantity': self.get_quantity(),
            'unit_price': self.get_unit_price(),
            'currency_id': self.get_currency_id(),
            'picture_url': self.get_picture_url()
        }
    json = property(get_json)


class MarketPreferences:
    """
    Clase abstracta para crear preferencias en el MarketPlace.

    """
    items = []
    payer = {}
    default_currency_id = CURRENCY_ID
    marketplace_fee = MARKETPLACE_FEE

    back_urls = {
            'failure': '',
            'pending': '',
            'success': ''
            }

    payment_methods = {
            'excluded_payment_methods': [], #by id {id: currency_id}
            'excluded_payment_types': [], #by id {id: types_id}
            'installments': 1 #
            }

    registered_items = [] # guarda los ID para no repetir items

    def __init__(self, *args, **kwargs):
        pass


    def set_item(self, item, force_append=False, *args, **kwargs):
        """
        Agrega un item a las preferencias No pisar éste método!.

        """
        if not isinstance(item, MarketItem):
            raise MPException("El item debe ser una instancia de MarketItem")

        if item.id in self.registered_items and not force_append:
            raise MPException("El item ID %s ya existe" % item.id)
        
        item.market_preferences = self
        self.items.append(item)
        self.registered_items.append(item.id)
        return self.get_items()

    def set_items(self, items, *args, **kwargs):
        """
        Agrega varios items en lote.

        """
        if not isinstance(items, (list, tuple)):
            items = [items]

        for item in items:
            self.set_item(item)

        return self.get_items()

    def remove_item(self, id, *ags, **kwargs):
        """
        Elimina un item del `preference` actual.

        """
        if not id in self.registered_items:
            raise MPException("El item ID %s no existe" % id)

        self.items = [item for item in self.get_items() if not item.id == id]
        self.registered_items = [item for item in self.registered_items if not item == id]

        return self.get_items()


    def get_items(self, *args, **kwargs):
        """
        Retorna la lista de items agregados.

        """
        return self.items

    def get_external_reference(self, *args, **kwargs):
        """
        Retorna las preferencias externas en caso de haberse creado.
        Por defecto devuelve la fecha en formato unix.
        Es recomendable crear un formato de preferencias propio, así se puede tener más control.

        """
        now = datetime.datetime.now()
        return now.strftime('%s')

    def get_payer(self, *args, **kwargs):
        """
        Retorna el `payer` si es que hay uno.

        """
        return self.payer

    def get_back_urls(self, *args, **kwargs):
        """
        Devuelve un diccionario con las URLs de retorno, `failure`, `pending`, `success`

        """
        return self.back_urls

    def get_payment_methods(self, *args, **kwargs):
        """
        Devuelve un diccionario con los medios y tipos de pago a excluir así como las cuotas.
        Por defecto no se excluye ningún método y ningún tipo de pago y se acepta un solo pago.

        El formato de retorno es:

        {
            'excluded_payment_methods': [
                {'id': 'amex'},
            ],

            'excluded_payment_types': [
                {'id': 'ticket'},
            ],

            'installments': 1 # 1,3,6,12.. etc
        }

        """
        return self.payment_methods

    def get_marketplace_fee(self, *args, **kwargs):
        """
        Debe retornar un `float` con la comisión para este `preference` o 0.

        """
        return self.marketplace_fee

    def get_currency(self, *args, **kwargs):
        """
        Setea de forma global la moneda.

        """
        return self.default_currency_id

    def get_json(self):
        """
        Devuelve el JSON que será enviado como argumento en el `preference`.

        """
        return {
            'items': [item.json for item in self.get_items()],
            'external_reference': self.get_external_reference(),
            'payer': self.get_payer(),
            'marketplace_fee': self.get_marketplace_fee(),
        }
    json = property(get_json)


class MarketApi:
    """
    MarketApi es una API muy simple para usar con el sistema MarketPlace de MercadoPago.

    Esta API pretende ser útil en escenarios no muy complejos, y tiene como fin ser lo más
    transparente posible al momento de interactuar con MercadoPago.

    Si aún no tenes una APP creada en mercadolibre podes ingresar a https://applications.mercadolibre.com.ar/list
    y crear la tuya, es un paso necesario para obtener el `client_id` y `client_secret`.

    """
    seller_preferences = None
    default_headers = {
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded'
            }

    default_client_args = {
            'client_id': None, # self.client_id
            'client_secret': None # self.client_secret
            }

    def __init__(self, client_id, client_secret, redirect_uri):
        """
        Instancia el MarketApi y crea la conexión.

        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

        self.default_client_args = {
                'client_id': self.client_id,
                'client_secret': self.client_secret
                }

        # conecta
        self._connect()

    def _call_api(self, url, args, headers=None):
        """
        Hace una llamada directa al `API entry point` de MercadoPago.

        El método espera la URL del `entry point` y los argumentos que serán enviados, 
        cómo opcional puede enviarse un header custom.

        """
        response = requests.post(url, args, headers=headers \
                or self.default_headers)
        
        if not response.status_code in \
                [requests.codes.ok, requests.codes.created]:
            raise MPException(response.status_code)

        return response.json()

    def _connect(self):
        """
        Obtiene token del MKT.

        """
        args = self.default_client_args.copy()
        args.update({'grant_type': 'client_credentials'})

        self.access_token = response = self._call_api(URL_AUTH, args)
        return self.access_token

    def get_client_code_link(self, redirect_uri=None, response_type='code'):
        """
        Devuelve la URL del link para la solicitud de autorización.

        """
        # https://auth.mercadolibre.com.ar/authorization?client_id=XXXXXXXXXXX 
        # &response_type=code&platform_id=mp
        # &redirect_uri=http://yourdomain.com/mp-auth/
        #
        # El callback devuelve por GET el code
        # ej: TG-XXXXXXXXXXXXXXXX 
        args = self.default_client_args.copy()
        args.update({
            'redirect_uri': redirect_uri or self.redirect_uri, 
            'response_type': response_type
            })
       
        action_url = URL_AUTHORIZATION + "?client_id=%(client_id)s&"\
                + "response_type=%(response_type)s&platform_id=mp&"\
                + "redirect_uri=%(redirect_uri)s"

        return action_url % args

    def get_seller_access_token(self, code, redirect_uri=None):
        """
        Obtiene la credencial a partir de un `code` resultado de una autorización.
        Devuelve el access_token.

        """
        args = self.default_client_args.copy()
        args.update({
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri or self.redirect_uri, 
            'code': code,
            })

        self.seller_access_token = self._call_api(URL_AUTH, args)
        return self.seller_access_token

    def refresh_seller_access_token(self, access_token=None):
        """
        Refrescar el access token para el seller code.
        Devuelve el access_token.

        """
        args = self.default_client_args.copy()
        args.update({
            'grant_type': 'refresh_token',
            'refresh_token': access_token or \
                    self.seller_access_token['refresh_token'],
            })

        self.seller_access_token = self._call_api(URL_AUTH, args)
        return self.seller_access_token

    def set_buy_preferences(self, preferences):
        """
        Define las preferencias para el botón de pago para éste seller.
        Retorna todo el JSON de la preferencia, luego hay que obtener el 

        """
        if not isinstance(preferences, MarketPreferences):
            raise MPException("El `preferences` debe ser una instancia de MarketPreferences")

        headers = self.default_headers.copy()
        headers.update({'content-type': 'application/json'})

        preferences_data = json.dumps(preferences.json)

        self.seller_preferences = self._call_api(URL_PREFERENCES + \
                '?access_token='+self.seller_access_token['access_token'], 
                preferences_data, headers)

        return self.seller_preferences

    def get_seller_prefereces(self, *args, **kwargs):
        """
        Devuelve las `preferences` que retorna MercadoPago luego de crear la `preferences`
        
        """
        return self.seller_preferences

    def get_preference_attr(self, key, *args, **kwargs):
        """
        Retorna el valor del atributo por key del `seller_preferences` que retorna MercadoPago.
        Pueden ser las siguientes `keys`:

        shipments
        auto_return
        marketplace
        expires
        expiration_date_to
        external_reference
        payer
        items
        id
        notification_url
        expiration_date_from
        payment_methods
        back_urls
        init_point
        collector_id
        client_id
        sandbox_init_point
        operation_type
        date_created
        marketplace_fee
        additional_info
        
        Para un detalle de que devuelve cada key revisar la documentación oficial de la API de MercadoPago.
        """

        if not self.seller_preferences:
            raise MPException("La instancia aun no tiene ningún `seller_preferences`, primero llamar a `set_buy_preferences`")

        return self.seller_preferences.get(key)

    def get_preference_id(self, *args, **kwargs):
        """
        Devuelve el ID del `preference` creado en MercadoPago.

        """
        return self.get_preference_attr('id')

    def get_collector_id(self, *args, **kwargs):
        """
        Devuelve el ID de MercadoPago del usaurio.

        """
        return self.get_preference_attr('collector_id')
        
    def get_init_point(self, *args, **kwargs):
        """
        Devuelve el `init_point` del botón.

        """
        return self.get_preference_attr('init_point')
        
    def get_sandbox_init_point(self, *args, **kwargs):
        """
        Devuelve el `sandbox_init_point` para el botón de prueba.

        """
        return self.get_preference_attr('sandbox_init_point') 
