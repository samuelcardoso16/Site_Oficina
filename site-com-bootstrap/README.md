# AutoPro Garage — Flask + API REST + SQLite

Sistema demonstrativo de gestão de oficina mecânica, com interface HTML/CSS/JavaScript e API REST em Flask.

## Requisitos
- Python 3.10 ou superior
- pip

## Instalação
Abra o terminal na pasta do projeto e execute:

```bash
python -m venv .venv
```

No Windows:
```bash
.venv\Scripts\activate
```

No Linux/macOS:
```bash
source .venv/bin/activate
```

Instale as dependências:
```bash
pip install -r requirements.txt
```

Inicie:
```bash
python app.py
```

Abra `http://127.0.0.1:5000`.

## Acesso inicial
- E-mail: `admin@autopro.local`
- Senha: `admin123`

Troque a chave `SECRET_KEY` em `app.py` antes de usar fora do ambiente local. A senha inicial é criada com hash. O banco `oficina.db` é criado automaticamente na primeira execução.

## Rotas principais da API
- `GET /api/health` — teste da API
- `POST /api/login` — login
- `POST /api/logout` — sair
- `GET /api/me` — sessão atual
- `GET /api/dashboard` — indicadores
- `/api/clients` — GET, POST; `/api/clients/<id>` — PUT, DELETE
- `/api/vehicles` — GET, POST; `/api/vehicles/<id>` — DELETE
- `/api/appointments` — GET, POST; `/api/appointments/<id>` — PATCH, DELETE
- `/api/orders` — GET, POST; `/api/orders/<id>` — PATCH, DELETE
- `/api/transactions` — GET, POST; `/api/transactions/<id>` — DELETE

As rotas administrativas exigem login. Os dados ficam em SQLite no computador que executa o Flask; para publicar na internet, configure servidor, HTTPS, chave secreta forte, proteção CSRF/rate limiting, backups e regras de acesso adequadas.
