# Recepcionista de voz — Estudio Lex Andina

Agente de voz que responde preguntas, agenda consultas y cobra con Culqi.
Construido con Spec-Driven Development: ver `specs/`.

## Setup

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
