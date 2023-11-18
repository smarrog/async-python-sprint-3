import unittest

from utils import CancellationToken


class CancellationTokenTestCase(unittest.TestCase):
    def test_initial_state(self):
        token: CancellationToken = CancellationToken()

        self.assertTrue(token.is_active)
        self.assertFalse(token.is_completed)
        self.assertFalse(token.is_cancelled)

    def test_state_after_cancel(self):
        token: CancellationToken = CancellationToken()
        token.cancel()

        self.assertFalse(token.is_active)
        self.assertFalse(token.is_completed)
        self.assertTrue(token.is_cancelled)

    def test_state_after_complete(self):
        token: CancellationToken = CancellationToken()
        token.complete()

        self.assertFalse(token.is_active)
        self.assertTrue(token.is_completed)
        self.assertFalse(token.is_cancelled)

    def test_state_immutable_after_cancel(self):
        token: CancellationToken = CancellationToken()
        token.cancel()
        token.complete()

        self.assertFalse(token.is_active)
        self.assertFalse(token.is_completed)
        self.assertTrue(token.is_cancelled)

    def test_state_immutable_after_complete(self):
        token: CancellationToken = CancellationToken()
        token.complete()
        token.cancel()

        self.assertFalse(token.is_active)
        self.assertTrue(token.is_completed)
        self.assertFalse(token.is_cancelled)

    def test_call_callback_when_cancel(self):
        counter: int = 0

        def callback():
            nonlocal counter

            counter = counter + 1

        token: CancellationToken = CancellationToken()
        token.on_cancel(callback)
        token.on_cancel(callback)

        token.cancel()

        self.assertEqual(2, counter)

    def test_call_is_not_called_when_complete(self):
        counter: int = 0

        def callback():
            nonlocal counter

            counter = counter + 1

        token: CancellationToken = CancellationToken()
        token.on_cancel(callback)
        token.on_cancel(callback)

        token.complete()

        self.assertEqual(0, counter)

    def test_remove_callback(self):
        counter: int = 0

        def callback():
            nonlocal counter

            counter = counter + 1

        token: CancellationToken = CancellationToken()
        token.on_cancel(callback)
        token.on_cancel(callback)
        token.remove_callback(callback)

        token.cancel()

        self.assertEqual(1, counter)

    def test_callbacks_cannot_be_called_twice(self):
        counter: int = 0

        def callback():
            nonlocal counter

            counter = counter + 1

        token: CancellationToken = CancellationToken()
        token.on_cancel(callback)
        token.on_cancel(callback)

        token.cancel()
        token.cancel()

        self.assertEqual(2, counter)
