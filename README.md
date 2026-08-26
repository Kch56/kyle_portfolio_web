# Kyle Hampton Portfolio

Flask portfolio for Kyle Hampton, including project, research, press, resume, contact, and blog pages.

## Run locally

1. Create a virtual environment.
2. Install dependencies using pip install -r requirements.txt.
3. Set the values shown in .env.example in your environment.
4. Run flask --app app run --debug.

## Blog administration

Visit /admin/login. Set BLOG_PASSWORD_HASH to a Werkzeug password hash. Generate one with Python and werkzeug.security.generate_password_hash.

The blog uses SQLite. On Render, attach a persistent disk and set BLOG_DB_PATH=/var/data/blog.db so posts survive deploys and restarts.

## Security

Secrets belong in environment variables, never in Git. The contact form reads all mail credentials from environment settings.

