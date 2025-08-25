-- 🔒 SCRIPT OPCIONAL PARA ATIVAR RLS NAS TABELAS "UNRESTRICTED"
-- Executar APENAS SE QUISER MÁXIMA SEGURANÇA

-- ⚠️ ATENÇÃO: Isso pode quebrar algumas funcionalidades se não houver policies adequadas

-- Ativar RLS nas tabelas analytics (cuidado - pode quebrar dashboard)
-- ALTER TABLE analytics_command_usage ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE analytics_daily_users ENABLE ROW LEVEL SECURITY;  
-- ALTER TABLE analytics_error_logs ENABLE ROW LEVEL SECURITY;

-- Ativar RLS no chat_history (pode quebrar logs)
-- ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;

-- Ativar RLS nas conquistas (pode quebrar sistema de gamificação)
-- ALTER TABLE conquistas ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE conquistas_usuario ENABLE ROW LEVEL SECURITY;

-- 📋 DEPOIS DE ATIVAR RLS, VOCÊ PRECISA CRIAR POLICIES:
-- CREATE POLICY "Users can view own data" ON analytics_command_usage
--   FOR SELECT USING (username = current_setting('app.current_username'));

-- ❗ IMPORTANTE: 
-- 1. Teste em ambiente de desenvolvimento primeiro
-- 2. Certifique-se de que o bot define current_setting() adequadamente
-- 3. O dashboard analytics pode parar de funcionar sem policies corretas
