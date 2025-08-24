# 🚀 CORREÇÃO URGENTE - OCR no Render

## ❌ PROBLEMA IDENTIFICADO:
Sua variável `GOOGLE_APPLICATION_CREDENTIALS` está incorreta:
- Valor atual: `credenciais/googlevision2.json`  
- Problema: Caminho local que não existe no Render

## ✅ SOLUÇÃO:

### 1. DELETAR no Render:
```
❌ GOOGLE_APPLICATION_CREDENTIALS
```

### 2. ADICIONAR no Render:
```
✅ GOOGLE_VISION_CREDENTIALS_JSON
```

### 3. VALOR da nova variável:
- Copie TODO o conteúdo do arquivo `credenciais/googlevision2.json`
- Cole como uma linha única (sem quebras)
- Exemplo: `{"type":"service_account","project_id":"...",...}`

## 🔄 APÓS MUDANÇAS:
1. Salve no Render
2. Redeploy manual
3. OCR funcionará! 🎉

O código já foi atualizado para funcionar com esta nova configuração.
