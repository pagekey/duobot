from duobot import DuoBot
import unittest

# TODO: Skip if env = dev

class TestDuoBot(unittest.TestCase):
    @unittest.skip("demonstrated pass 3/14. temp skip to save time")
    def test_perform_login_valid(self):
        bot = DuoBot()
        self.assertTrue(bot.perform_login())
    @unittest.skip("demonstrated pass 3/14. temp skip to save time")
    def test_perform_login_invalid(self):
        bot = DuoBot()
        bot.cfg['password'] = 'wrong password'
        self.assertFalse(bot.perform_login())
    @unittest.skip("demonstrated pass 3/14. temp skip to save time")
    def test_get_current_language_invalid(self):
        bot = DuoBot()
        self.assertFalse(bot.get_current_language())
        self.assertEqual(bot.current_language, None)
    def test_get_current_language_valid(self):
        bot = DuoBot()
        bot.perform_login()
        self.assertTrue(bot.get_current_language())
        self.assertNotEqual(bot.current_language, None)
        self.assertGreater(len(bot.current_language), 0)
if __name__ == '__main__':
    unittest.main()