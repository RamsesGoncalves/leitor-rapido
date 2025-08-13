# 📚 Leitor Rápido

Sistema de leitura rápida de PDFs com controle de velocidade e tokenização inteligente.

## ✨ Funcionalidades

- **Upload de PDF**: Processamento automático de documentos
- **Leitura Dinâmica**: Controle de velocidade (60-1200 PPM)
- **Visualização Múltipla**: 1, 2 ou 3 tokens por tela
- **Regras Inteligentes**: 
  - Agrupamento de monossílabos
  - Correção de hífens
  - Ponto final encerra janela automaticamente
- **Navegação**: Play/pause, anterior/próxima, salto por página
- **Preview**: Visualização da próxima janela
- **PDF Integrado**: Sincronização com página atual

## 🛠️ Tecnologias

### Backend
- **Python 3.8+**
- **FastAPI**: API REST
- **pdfplumber**: Extração de texto de PDF
- **Uvicorn**: Servidor ASGI

### Frontend
- **React 18**: Interface de usuário
- **TypeScript**: Tipagem estática
- **Vite**: Build tool
- **Tailwind CSS**: Estilização
- **Framer Motion**: Animações

## 🚀 Como Executar

### Pré-requisitos
- Python 3.8+
- Node.js 16+

### Backend
```bash
cd app/
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd web/
npm install
npm run dev
```

Acesse: http://localhost:5173

## 📋 Regras de Tokenização

1. **Monossílabos**: Agrupam com próxima palavra ("em casa")
2. **Hífens**: Correção de quebras de linha e compostas
3. **Pontuação**: Multiplicadores de tempo por contexto
4. **Ponto Final**: Sempre encerra a janela de visualização
5. **Complexidade**: Ajuste de tempo por tamanho da palavra

## 🎯 Configurações

- **PPM**: 60-1200 palavras por minuto
- **Palavras por Tela**: 1, 2 ou 3 tokens
- **Preview**: Opcional da próxima janela
- **Página Inicial**: Salto para página específica

## 📄 Licença

MIT License
