import unittest
from unittest.mock import patch, MagicMock
from mail_service import MailService
import telegram_bot

class TestMailService(unittest.TestCase):
    def setUp(self):
        self.service = MailService()

    @patch("requests.get")
    def test_get_domains(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "hydra:member": [
                {"domain": "example.com", "isAvailable": True},
                {"domain": "test.com", "isAvailable": False}
            ]
        }
        mock_get.return_value = mock_resp

        domains = self.service.get_domains()
        self.assertEqual(domains, ["example.com"])

    @patch("requests.post")
    @patch("mail_service.MailService.get_domains")
    def test_create_account(self, mock_domains, mock_post):
        mock_domains.return_value = ["example.com"]

        mock_reg = MagicMock()
        mock_reg.status_code = 201
        mock_reg.json.return_value = {"id": "acc123"}

        mock_token = MagicMock()
        mock_token.status_code = 200
        mock_token.json.return_value = {"token": "secret_token_123"}

        mock_post.side_effect = [mock_reg, mock_token]

        email, token, acc_id = self.service.create_account(custom_prefix="user123")
        self.assertEqual(email, "user123@example.com")
        self.assertEqual(token, "secret_token_123")
        self.assertEqual(acc_id, "acc123")

    @patch("requests.get")
    def test_get_messages(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "hydra:member": [
                {"id": "msg1", "subject": "Test Email", "from": {"address": "sender@test.com"}}
            ]
        }
        mock_get.return_value = mock_resp

        msgs = self.service.get_messages("test_token")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["id"], "msg1")

    @patch("requests.delete")
    def test_delete_message(self, mock_delete):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_delete.return_value = mock_resp

        success = self.service.delete_message("token", "msg1")
        self.assertTrue(success)


class TestTelegramBotMarkups(unittest.TestCase):
    def test_build_main_menu_no_session(self):
        markup = telegram_bot.build_main_menu(99999)
        self.assertIsNotNone(markup)
        # Check rows structure
        buttons = [btn for row in markup.keyboard for btn in row]
        button_texts = [b.text for b in buttons]
        self.assertTrue(any("Create Temp Email Now" in t for t in button_texts))

    def test_build_main_menu_with_session(self):
        telegram_bot.user_sessions[111] = {
            "email": "test@example.com",
            "token": "tok",
            "account_id": "acc"
        }
        markup = telegram_bot.build_main_menu(111)
        buttons = [btn for row in markup.keyboard for btn in row]
        button_texts = [b.text for b in buttons]
        self.assertTrue(any("Check Inbox" in t for t in button_texts))
        self.assertTrue(any("Copy Current Email" in t for t in button_texts))

    def test_build_inbox_menu(self):
        messages = [
            {"id": "m1", "subject": "Welcome!", "from": {"address": "admin@site.com"}}
        ]
        markup = telegram_bot.build_inbox_menu(messages)
        buttons = [btn for row in markup.keyboard for btn in row]
        button_texts = [b.text for b in buttons]
        self.assertTrue(any("Welcome!" in t for t in button_texts))

    def test_create_bot_instance(self):
        bot = telegram_bot.create_bot("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        self.assertIsNotNone(bot)

if __name__ == "__main__":
    unittest.main()
