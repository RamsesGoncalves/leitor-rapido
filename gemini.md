# Gemini Project: Backend para Leitor Rápido de PDF

Este projeto irá criar a API de backend para um aplicativo de leitura rápida, capaz de processar arquivos PDF enviados por upload.

## 1. Estrutura do Projeto

Crie a seguinte estrutura de arquivos e diretórios:

```
/
|-- .gitignore
|-- app/
|   |-- __init__.py
|   |-- main.py
|   |-- processing.py
|   |-- models.py
|   |-- storage.py
|-- requirements.txt
|-- uploads/
```

O diretório `uploads/` será usado para armazenar temporariamente os arquivos PDF. Adicione `uploads/` e `__pycache__/` ao arquivo `.gitignore`.

## 2. Dependências

Popule o arquivo `requirements.txt` com as seguintes dependências:

```txt
fastapi
uvicorn[standard]
python-multipart
pdfplumber
```

## 3. Código Fonte

Use os seguintes prompts para gerar o código para cada arquivo.

### Arquivo: `app/storage.py`

**Prompt:**
> Crie um dicionário Python simples, em memória, para atuar como nosso banco de dados temporário. Ele deve ser chamado `db`. Este dicionário irá armazenar o status e os dados dos documentos processados. As chaves serão o `document_id` e os valores serão outros dicionários contendo `status` e `words`. 
> 
> Exemplo: `{'doc-123': {'status': 'completed', 'words': ['olá', 'mundo']}}`

### Arquivo: `app/models.py`

**Prompt:**
> Crie os modelos Pydantic para esta API. Precisamos de:
> - Um modelo `DocumentStatus` que contenha os campos `status: str` e `word_count: int`.
> - Um modelo `DocumentWords` que contenha um campo `words: list[str]`.
> - Um modelo `DocumentUploadResponse` que contenha os campos `document_id: str` e `status: str`.

### Arquivo: `app/processing.py`

**Prompt:**
> Crie uma função chamada `process_pdf`. Esta função deve:
> - Receber como argumentos o `document_id` (string) e o `file_path` (string) do PDF.
> - Usar a biblioteca `pdfplumber` para abrir o arquivo no `file_path`.
> - Iterar por todas as páginas do PDF, extrair o texto de cada uma e concatená-lo em uma única string.
> - Limpar o texto, substituindo caracteres de nova linha (`\n`) por espaços.
> - Tokenizar o texto, dividindo a string em uma lista de palavras usando espaços como delimitador.
> - Atualizar nosso `db` (do módulo storage) para aquele `document_id`: o status deve ser 'completed' e o campo `words` deve conter a lista de palavras gerada.
> - A função deve ser executada em segundo plano para não bloquear a resposta da API. Use `background_tasks` do FastAPI para isso.

### Arquivo: `app/main.py`

**Prompt:**
> Crie a aplicação principal da API usando FastAPI. O código deve:
> - Importar `FastAPI`, `UploadFile`, `File`, `BackgroundTasks` e os módulos locais (storage, models, processing).
> - Instanciar o app FastAPI.
> - Importar o `db` do storage.
> 
> **Criar um endpoint POST `/documents` que:**
> - Aceite um `UploadFile` e injete `BackgroundTasks`.
> - Valide se o `content_type` do arquivo é 'application/pdf'. Se não for, retorne um erro 400.
> - Gere um `document_id` único usando `uuid.uuid4()`.
> - Salve o arquivo PDF no diretório `uploads/` com um nome de arquivo seguro.
> - Adicione uma entrada inicial no `db` para o novo `document_id` com o status 'processing'.
> - Adicione a função `process_pdf` como uma tarefa de fundo (`background_tasks.add_task`).
> - Retorne uma resposta 202 Accepted com o `document_id` e o status 'processing', usando o modelo `DocumentUploadResponse`.
> 
> **Criar um endpoint GET `/documents/{document_id}/status` que:**
> - Receba um `document_id`.
> - Verifique se o ID existe no `db`. Se não, retorne um erro 404.
> - Calcule a contagem de palavras se o processamento estiver completo.
> - Retorne o status e a contagem de palavras usando o modelo `DocumentStatus`.
> 
> **Criar um endpoint GET `/documents/{document_id}/words` que:**
> - Receba um `document_id`.
> - Verifique se o ID existe e se o status é 'completed'. Se não, retorne um erro 404 ou 422.
> - Se estiver completo, retorne a lista de palavras usando o modelo `DocumentWords`.
