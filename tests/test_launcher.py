
import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Adicionar o diretório raiz ao sys.path para permitir a importação do launcher
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestLauncher(unittest.TestCase):

    @patch('launcher.load_environment')
    @patch('launcher.apply_migrations')
    @patch('launcher.start_telegram_bot')
    @patch('launcher.start_dashboard')
    def run_main_with_env(self, env_vars, mock_start_dashboard, mock_start_bot, mock_apply_migrations, mock_load_env):
        """Helper para rodar a função main com variáveis de ambiente mockadas."""
        mock_load_env.return_value = True
        
        with patch.dict('os.environ', env_vars, clear=True):
            # Importar o launcher aqui para que ele use as variáveis de ambiente mockadas
            import launcher
            launcher.main()

    def test_railway_environment_starts_bot(self):
        """Testa se o bot inicia no ambiente Railway."""
        env = {
            'RAILWAY_ENVIRONMENT': 'production',
            'PORT': '8080',
            'TELEGRAM_TOKEN': 'fake_token',
            'DATABASE_URL': 'fake_db_url'
        }
        with patch('launcher.start_telegram_bot') as mock_start_bot, \
             patch('launcher.start_dashboard') as mock_start_dashboard:
            
            self.run_main_with_env(env)
            mock_start_bot.assert_called_once()
            mock_start_dashboard.assert_not_called()

    def test_render_web_service_starts_dashboard(self):
        """Testa se o dashboard inicia no ambiente Render Web Service."""
        env = {
            'RENDER': 'true',
            'PORT': '10000',
            'TELEGRAM_TOKEN': 'fake_token',
            'DATABASE_URL': 'fake_db_url'
        }
        with patch('launcher.start_telegram_bot') as mock_start_bot, \
             patch('launcher.start_dashboard') as mock_start_dashboard:
            
            self.run_main_with_env(env)
            mock_start_bot.assert_not_called()
            mock_start_dashboard.assert_called_once()

    def test_render_worker_starts_bot(self):
        """Testa se o bot inicia no ambiente Render Worker."""
        env = {
            'RENDER': 'true',
            'TELEGRAM_TOKEN': 'fake_token',
            'DATABASE_URL': 'fake_db_url'
        }
        with patch('launcher.start_telegram_bot') as mock_start_bot, \
             patch('launcher.start_dashboard') as mock_start_dashboard:
            
            self.run_main_with_env(env)
            mock_start_bot.assert_called_once()
            mock_start_dashboard.assert_not_called()

    def test_force_bot_mode(self):
        """Testa se o modo 'bot' forçado inicia o bot."""
        env = {
            'CONTACOMIGO_MODE': 'bot',
            'PORT': '8080', # Mesmo com PORT, deve forçar o bot
            'RAILWAY_ENVIRONMENT': 'production',
            'TELEGRAM_TOKEN': 'fake_token',
            'DATABASE_URL': 'fake_db_url'
        }
        with patch('launcher.start_telegram_bot') as mock_start_bot, \
             patch('launcher.start_dashboard') as mock_start_dashboard:
            
            self.run_main_with_env(env)
            mock_start_bot.assert_called_once()
            mock_start_dashboard.assert_not_called()

    def test_force_dashboard_mode(self):
        """Testa se o modo 'dashboard' forçado inicia o dashboard."""
        env = {
            'CONTACOMIGO_MODE': 'dashboard',
            'RAILWAY_ENVIRONMENT': 'production', # Mesmo em Railway, deve forçar o dashboard
            'TELEGRAM_TOKEN': 'fake_token',
            'DATABASE_URL': 'fake_db_url'
        }
        with patch('launcher.start_telegram_bot') as mock_start_bot, \
             patch('launcher.start_dashboard') as mock_start_dashboard:
            
            self.run_main_with_env(env)
            mock_start_bot.assert_not_called()
            mock_start_dashboard.assert_called_once()

    @patch('threading.Thread')
    def test_local_mode_starts_both(self, mock_thread):
        """Testa se o modo local inicia tanto o bot quanto o dashboard."""
        env = {
            'TELEGRAM_TOKEN': 'fake_token',
            'DATABASE_URL': 'fake_db_url'
        }
        
        # Mock para a thread do bot
        mock_bot_thread = MagicMock()
        mock_thread.return_value = mock_bot_thread

        with patch('launcher.start_telegram_bot') as mock_start_bot, \
             patch('launcher.start_dashboard') as mock_start_dashboard:
            
            self.run_main_with_env(env)
            
            # Verifica se a thread do bot foi criada e iniciada
            mock_thread.assert_called_once_with(target=mock_start_bot, daemon=True)
            mock_bot_thread.start.assert_called_once()
            
            # Verifica se o dashboard foi iniciado na thread principal
            mock_start_dashboard.assert_called_once()


if __name__ == '__main__':
    unittest.main()
