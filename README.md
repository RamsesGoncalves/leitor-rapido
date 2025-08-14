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
 - **Barra Lateral Persistente**: lista seus PDFs processados, progresso (última página/índice) e exclusão
 - **Salvamento Automático**: o progresso é salvo conforme você lê
 - **Atualização Automática**: a lista de documentos atualiza periodicamente e após uploads
 - **Responsivo**: layout adaptado para desktop e dispositivos móveis

## 🛠️ Tecnologias

### Backend
- **Python 3.8+**
- **FastAPI**: API REST
- **pdfplumber**: Extração de texto de PDF
- **Uvicorn**: Servidor ASGI
 - **SQLite**: Persistência simples (metadados e progresso)

### Frontend
- **React 18**: Interface de usuário
- **TypeScript**: Tipagem estática
- **Vite**: Build tool
- **Tailwind CSS**: Estilização
- **Framer Motion**: Animações
 - **MagicUI**: Cartões e componentes com visual moderno

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

## 🗄️ Persistência e Estrutura

- O backend cria automaticamente um banco SQLite em `data/db.sqlite3` no startup.
- PDFs enviados vão para `uploads/` e os tokens/weights são salvos como JSON `*_tokens.json`.
- Endpoints principais:
  - `POST /documents` — faz upload e inicia processamento
  - `GET /documents` — lista documentos com status e progresso
  - `GET /documents/{id}/status|words|tokens|file` — dados do documento
  - `POST /documents/{id}/progress?last_index&last_page` — salva progresso
  - `DELETE /documents/{id}` — remove o documento do catálogo

## 📋 Regras de Tokenização

1. **Monossílabos**: Agrupam com próxima palavra ("em casa")
2. **Hífens**: Correção de quebras de linha e compostas
3. **Pontuação**: Multiplicadores de tempo por contexto
4. **Ponto Final**: Sempre encerra a janela de visualização
5. **Complexidade**: Ajuste de tempo por tamanho da palavra

## 📱 Responsividade

- A UI utiliza grid responsivo; em telas grandes a barra lateral fica fixa, em mobile ela recolhe e aparece acima do player.
- Componentes com `MagicCard` e transições suaves com `framer-motion`.

## 🔐 Boas práticas

- Não faça commit de `.env` ou dados sensíveis.
- `uploads/*.pdf` e `data/db.sqlite3` permanecem fora do Git (checar `.gitignore`).

## 🎯 Configurações

- **PPM**: 60-1200 palavras por minuto
- **Palavras por Tela**: 1, 2 ou 3 tokens
- **Preview**: Opcional da próxima janela
- **Página Inicial**: Salto para página específica

## 📄 Licença

MIT License
