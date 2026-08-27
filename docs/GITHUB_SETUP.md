# Publish to GitHub

Create an empty public repository named `open-data-intelligence-pipeline`, then run these commands
from the project directory. Replace the URL with the one GitHub shows for your account.

```bash
git init
git add .
git commit -m "Build open-data intelligence pipeline MVP"
git branch -M main
git remote add origin https://github.com/DrevitskyLV/open-data-intelligence-pipeline.git
git push -u origin main
```

Before pushing, verify that `.env`, database files and private data are not staged:

```bash
git status
git diff --cached
```

Recommended repository description:

> FastAPI pipeline for idempotent data ingestion, entity normalization, relationship discovery
> and explainable analytics. PostgreSQL, Alembic, Docker, pytest and GitHub Actions.

Recommended topics:

```text
python fastapi postgresql sqlalchemy alembic docker pytest data-pipeline open-data
```

After pushing, confirm that the Actions tab contains a green CI run. Add the repository to the
Featured section of LinkedIn only after that check is green.

