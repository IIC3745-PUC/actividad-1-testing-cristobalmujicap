import unittest
from unittest.mock import Mock, patch

from src.models import CartItem, Order
from src.pricing import PricingService, PricingError
from src.checkout import CheckoutService, ChargeResult

class TestCheckoutService(unittest.TestCase):

    def setUp(self):
        # 1. Arrange: Preparamos los "Test Doubles" usando Mock
        self.mock_payments = Mock()
        self.mock_email = Mock()
        self.mock_fraud = Mock()
        self.mock_repo = Mock()
        self.mock_pricing = Mock()

        # Inyectamos los mocks en el servicio
        self.checkout_service = CheckoutService(
            payments=self.mock_payments,
            email=self.mock_email,
            fraud=self.mock_fraud,
            repo=self.mock_repo,
            pricing=self.mock_pricing
        )

        # Un carrito de compras dummy para usar en los tests
        self.dummy_items = [CartItem(sku="SKU_TEST", unit_price_cents=1000, qty=1)]

    # --- Test de Inicialización ---
    def test_init_without_pricing(self):
        service = CheckoutService(
            payments=self.mock_payments,
            email=self.mock_email,
            fraud=self.mock_fraud,
            repo=self.mock_repo
        )
        self.assertIsNotNone(service.pricing)

    # --- Tests de validaciones tempranas ---
    def test_invalid_user(self):
        result = self.checkout_service.checkout(
            user_id="   ", 
            items=self.dummy_items,
            payment_token="token_123",
            country="CL"
        )
        self.assertEqual(result, "INVALID_USER")

    def test_invalid_cart(self):
        self.mock_pricing.total_cents.side_effect = PricingError("test_error")
        
        result = self.checkout_service.checkout(
            user_id="user_1",
            items=self.dummy_items,
            payment_token="token_123",
            country="CL"
        )
        self.assertEqual(result, "INVALID_CART:test_error")

    # --- Tests de Servicios Externos ---
    def test_rejected_fraud(self):
        self.mock_pricing.total_cents.return_value = 1000
        self.mock_fraud.score.return_value = 85
        
        result = self.checkout_service.checkout(
            user_id="user_1",
            items=self.dummy_items,
            payment_token="token_123",
            country="CL"
        )
        self.assertEqual(result, "REJECTED_FRAUD")

    def test_payment_failed(self):
        self.mock_pricing.total_cents.return_value = 1000
        self.mock_fraud.score.return_value = 10
        self.mock_payments.charge.return_value = ChargeResult(ok=False, reason="Fondos insuficientes")

        result = self.checkout_service.checkout(
            user_id="user_1",
            items=self.dummy_items,
            payment_token="token_123",
            country="CL"
        )
        self.assertEqual(result, "PAYMENT_FAILED:Fondos insuficientes")

# --- Tests de Flujo de Éxito ---
    @patch('src.checkout.uuid') 
    def test_checkout_success(self, mock_uuid):
        mock_uuid.uuid4.return_value = "uuid-super-seguro"
        self.mock_pricing.total_cents.return_value = 1000
        self.mock_fraud.score.return_value = 10
        self.mock_payments.charge.return_value = ChargeResult(ok=True, charge_id="ch_123")

        result = self.checkout_service.checkout(
            user_id="user_1",
            items=self.dummy_items,
            payment_token="token_123",
            country="CL"
        )

        self.assertEqual(result, "OK:uuid-super-seguro")
        self.mock_repo.save.assert_called_once()
        self.mock_email.send_receipt.assert_called_once_with("user_1", "uuid-super-seguro", 1000)

    @patch('src.checkout.uuid')
    def test_checkout_success_no_charge_id(self, mock_uuid):
        mock_uuid.uuid4.return_value = "uuid-super-seguro"
        self.mock_pricing.total_cents.return_value = 1000
        self.mock_fraud.score.return_value = 10
        self.mock_payments.charge.return_value = ChargeResult(ok=True, charge_id=None)

        self.checkout_service.checkout(
            user_id="user_1",
            items=self.dummy_items,
            payment_token="token_123",
            country="CL"
        )

        saved_order = self.mock_repo.save.call_args[0][0]
        self.assertEqual(saved_order.payment_charge_id, "UNKNOWN")

if __name__ == '__main__':
    unittest.main()