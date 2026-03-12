import unittest
from unittest.mock import Mock

from src.models import CartItem, Order
from src.pricing import PricingService, PricingError

class TestPricingService(unittest.TestCase):

    def setUp(self):
        # Se ejecuta antes de cada test para darnos un entorno limpio
        self.pricing = PricingService()

    # --- Tests para subtotal_cents ---
    def test_subtotal_cents_success(self):
        items = [
            CartItem(sku="SKU01", unit_price_cents=1500, qty=2),
            CartItem(sku="SKU02", unit_price_cents=2000, qty=1)
        ]
        # 2*1500 + 1*2000 = 5000
        self.assertEqual(self.pricing.subtotal_cents(items), 5000)

    def test_subtotal_cents_empty_cart(self):
        self.assertEqual(self.pricing.subtotal_cents([]), 0)

    def test_subtotal_cents_invalid_qty(self):
        items = [CartItem(sku="SKU01", unit_price_cents=1000, qty=0)]
        with self.assertRaisesRegex(PricingError, "qty must be > 0"):
            self.pricing.subtotal_cents(items)

    def test_subtotal_cents_invalid_price(self):
        items = [CartItem(sku="SKU01", unit_price_cents=-500, qty=1)]
        with self.assertRaisesRegex(PricingError, "unit_price_cents must be >= 0"):
            self.pricing.subtotal_cents(items)

    # --- Tests para apply_coupon ---
    def test_apply_coupon_none_or_empty(self):
        subtotal = 10000
        self.assertEqual(self.pricing.apply_coupon(subtotal, None), 10000)
        self.assertEqual(self.pricing.apply_coupon(subtotal, ""), 10000)
        self.assertEqual(self.pricing.apply_coupon(subtotal, "   "), 10000)

    def test_apply_coupon_save10(self):
        # 10% de descuento de 10000 es 1000. Queda 9000.
        self.assertEqual(self.pricing.apply_coupon(10000, "SAVE10"), 9000)
        # Probamos que funcione con espacios y minúsculas (por el .strip().upper())
        self.assertEqual(self.pricing.apply_coupon(10000, " save10 "), 9000)

    def test_apply_coupon_clp2000(self):
        # Descuento fijo de 2000
        self.assertEqual(self.pricing.apply_coupon(5000, "CLP2000"), 3000)
        # No debe bajar de 0
        self.assertEqual(self.pricing.apply_coupon(1500, "CLP2000"), 0)

    def test_apply_coupon_invalid(self):
        with self.assertRaisesRegex(PricingError, "invalid coupon"):
            self.pricing.apply_coupon(10000, "INVALIDO")

    # --- Tests para tax_cents ---
    def test_tax_cents_countries(self):
        subtotal = 10000
        self.assertEqual(self.pricing.tax_cents(subtotal, "CL"), 1900)  # 19%
        self.assertEqual(self.pricing.tax_cents(subtotal, "EU"), 2100)  # 21%
        self.assertEqual(self.pricing.tax_cents(subtotal, "US"), 0)     # 0%
        # Prueba con espacios y minúsculas
        self.assertEqual(self.pricing.tax_cents(subtotal, " cl "), 1900)

    def test_tax_cents_invalid_country(self):
        with self.assertRaisesRegex(PricingError, "unsupported country"):
            self.pricing.tax_cents(10000, "AR")

    # --- Tests para shipping_cents ---
    def test_shipping_cents_cl(self):
        self.assertEqual(self.pricing.shipping_cents(19999, "CL"), 2500) # Menor a 20k
        self.assertEqual(self.pricing.shipping_cents(20000, "CL"), 0)    # Mayor o igual a 20k

    def test_shipping_cents_us_eu(self):
        self.assertEqual(self.pricing.shipping_cents(10000, "US"), 5000)
        self.assertEqual(self.pricing.shipping_cents(10000, "EU"), 5000)

    def test_shipping_cents_invalid_country(self):
        with self.assertRaisesRegex(PricingError, "unsupported country"):
            self.pricing.shipping_cents(10000, "AR")
	
# --- Tests para total_cents ---
    def test_total_cents(self):
        # Flujo completo: subtotal = 10000
        items = [CartItem(sku="SKU01", unit_price_cents=10000, qty=1)]
        
        # Con cupon SAVE10 -> net_subtotal = 9000
        # País CL -> tax = 19% de 9000 = 1710
        # País CL (net_subtotal < 20000) -> shipping = 2500
        # Total esperado = 9000 + 1710 + 2500 = 13210
        expected_total = 13210
        
        self.assertEqual(
            self.pricing.total_cents(items, "SAVE10", "CL"), 
            expected_total
        )

if __name__ == '__main__':
    unittest.main()