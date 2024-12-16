# escolas.org - Backend

Este repositório contém o código do servidor backend para o projeto escolas.org.

## Pré-requisitos

*   Python (>= 3.11.7)
*   Gerenciador de pacotes pip (geralmente incluído com o Python)

## Instalação e Execução

1.  **Baixe os arquivos .csv:**
    *   Acesse a pasta compartilhada [aqui](https://drive.google.com/drive/u/2/folders/1thS9IBs2eFAWvM4dKCJeRUe-IeoZwOB2).
    *   Baixe todos os arquivos .csv (censos) para uma pasta local.

2.  **Clone o repositório:**

    ```bash
    git clone <link_do_repositorio_backend>
    ```

3.  **Prepare os dados do censo:**

    *   Crie uma pasta chamada `censos` na raiz do repositório.
    *   Mova todos os arquivos .csv baixados na etapa 1 para dentro da pasta `censos`.

4.  **Configuração do ambiente virtual:**

    *   Navegue até a pasta raiz do projeto no terminal.
    *   Crie e ative um ambiente virtual:

        *   **Windows:**

            ```bash
            python -m venv venv
            venv\Scripts\activate
            ```

        *   **Linux/macOS:**

            ```bash
            python3 -m venv venv
            source venv/bin/activate
            ```

5.  **Instale as dependências:**

    ```bash
    pip install -r requirements.txt
    ```

6.  **Migrações do banco de dados:**

    ```bash
    py manage.py migrate
    ```

7.  **Importação dos dados do censo (opcional, mas demorado - veja a alternativa abaixo):**

    ```bash
    py manage.py import_censos
    ```

    Este comando pode levar cerca de 50 minutos para ser concluído, pois processa aproximadamente um milhão de registros.

8.  **Executando o servidor:**

    ```bash
    py manage.py runserver
    ```

    O servidor estará disponível em `http://127.0.0.1:8000/` (ou outro endereço/porta indicados no console).

## Importação Rápida do Banco de Dados (Alternativa à Etapa 7)**

Para pular a importação demorada dos dados do censo:

1.  Acesse a pasta compartilhada [aqui](https://drive.google.com/drive/u/2/folders/1thS9IBs2eFAWvM4dKCJeRUe-IeoZwOB2).
2.  Baixe o arquivo `db.sqlite3`.
3.  Coloque o arquivo `db.sqlite3` na pasta raiz do repositório.
4.  Pule a etapa 7 e execute diretamente o comando `py manage.py runserver`.

## Observações

*   Certifique-se de que o frontend não será executado sem o backend.

## Suporte

Em caso de dúvidas, entre em contato por [email](seu_email).
