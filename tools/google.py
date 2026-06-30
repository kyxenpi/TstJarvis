import json
import datetime
import io
import time
import ast
import base64
import os
from pathlib import Path
from typing import Any, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

from tools.base import tool, IS_CLOUD
from config import settings
from core.security import SecurityLevel
from core.logger import setup_logger
from database.memory_db import db

logger = setup_logger("GoogleTools")

MAX_RETRIES = 3
RETRY_DELAY = 2


def safe_parse_args(args: Any) -> Dict[str, Any]:
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        args_str = args.strip()
        try:
            return json.loads(args_str)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(args_str)
                if isinstance(parsed, dict):
                    return parsed
            except Exception as e:
                logger.error(f"Falha ao parsear args: {e}")
    return {}


def _extract_id(d: Dict[str, Any]) -> Optional[str]:
    for key in ("document_id", "documentId", "documentid", "file_id", "id"):
        if key in d and d[key]:
            return str(d[key])
    return None


def _extract_content(d: Dict[str, Any]) -> str:
    for key in ("content", "text", "body"):
        if key in d and d[key]:
            return d[key]
    return ""


def get_google_credentials():
    creds = None
    token_path = Path('token.json')

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), settings.SCOPES)
    elif settings.GOOGLE_TOKEN_JSON:
        try:
            creds = Credentials.from_authorized_user_info(
                json.loads(settings.GOOGLE_TOKEN_JSON), settings.SCOPES
            )
        except Exception as e:
            logger.error(f"Erro no GOOGLE_TOKEN_JSON: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.warning(f"Falha ao renovar token: {e}")
                if "invalid_grant" in str(e) and token_path.exists():
                    token_path.unlink()
                creds = None

        if not creds:
            if IS_CLOUD:
                raise Exception(
                    "Credenciais Google expiradas. Configure GOOGLE_TOKEN_JSON "
                    "como variável de ambiente no Render com um token renovado."
                )
            if Path('credentials.json').exists():
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', settings.SCOPES
                )
                creds = flow.run_local_server(port=0)
            elif settings.GOOGLE_CREDENTIALS_JSON:
                flow = InstalledAppFlow.from_client_config(
                    json.loads(settings.GOOGLE_CREDENTIALS_JSON), settings.SCOPES
                )
                creds = flow.run_local_server(port=0)
            else:
                raise Exception("Credenciais Google não encontradas.")

            if not settings.GOOGLE_TOKEN_JSON:
                token_path.write_text(creds.to_json())

    return creds


def _retry_on_error(func, *args, **kwargs):
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except HttpError as e:
            last_error = e
            if e.resp.status in (429, 500, 503):
                wait = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Retry {attempt+1}/{MAX_RETRIES} após {wait}s: {e}")
                time.sleep(wait)
                continue
            raise
    raise last_error


@tool("google_docs", security_level=SecurityLevel.MEDIUM, cloud_compatible=True)
def google_docs_tool(args: Any) -> Dict[str, Any]:
    """Cria ou edita documentos no Google Docs. Se 'document_id' existir, atualiza; senão, cria novo."""
    try:
        creds = get_google_credentials()
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)

        args_dict = safe_parse_args(args)
        if not args_dict and isinstance(args, str):
            args_dict = {"title": f"Doc Koda - {datetime.date.today()}", "content": args}

        doc_id = _extract_id(args_dict)
        content = _extract_content(args_dict)
        title = args_dict.get("title", f"Doc Koda - {datetime.date.today()}")

        if doc_id:
            try:
                doc = _retry_on_error(
                    docs_service.documents().get, documentId=doc_id
                )
                doc_content = doc.get('body', {}).get('content', [])
                existing_text = "".join(
                    elem.get('paragraph', {}).get('elements', [{}])[0]
                    .get('textRun', {}).get('content', '')
                    for elem in doc_content
                    if 'paragraph' in elem
                )

                linhas_novas = [l for l in content.split('\n')
                                if l.strip() and l.strip() not in existing_text]
                if not linhas_novas:
                    return {"success": True, "result": {"document_id": doc_id, "status": "Sem novidades."}}

                requests_body = []
                for linha in linhas_novas:
                    requests_body.append({
                        "insertText": {
                            "location": {"index": 1},
                            "text": linha + "\n"
                        }
                    })
                if requests_body:
                    _retry_on_error(
                        docs_service.documents().batchUpdate,
                        documentId=doc_id,
                        body={"requests": requests_body}
                    )
                return {"success": True, "result": {"document_id": doc_id, "status": "Atualizado."}}
            except Exception as e:
                return {"success": False, "error": f"Erro ao acessar doc: {e}"}

        file_metadata = {'name': title, 'mimeType': 'application/vnd.google-apps.document'}
        content_html = content.replace('\n', '<br>')
        fh = io.BytesIO(f"<html><body>{content_html}</body></html>".encode('utf-8'))
        media = MediaIoBaseUpload(fh, mimetype='text/html', resumable=True)

        doc_file = _retry_on_error(
            lambda: drive_service.files().create(
                body=file_metadata, media_body=media, fields='id'
            ).execute()
        )
        new_id = doc_file.get('id')
        db.save_metadata("last_google_doc_id", new_id)
        return {"success": True, "result": {"document_id": new_id, "status": "Criado."}}

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("google_docs_read", security_level=SecurityLevel.MEDIUM, cloud_compatible=True)
def google_docs_read(args: Any) -> Dict[str, Any]:
    """Lê o conteúdo de um Google Docs pelo ID."""
    try:
        creds = get_google_credentials()
        docs_service = build('docs', 'v1', credentials=creds)

        args_dict = safe_parse_args(args)
        doc_id = args_dict.get("document_id") or args_dict.get("id") or args_dict.get("doc_id") or ""
        if not doc_id:
            doc_id = db.get_metadata("last_google_doc_id")
            if not doc_id:
                return {"success": False, "error": "Nenhum document_id fornecido ou salvo."}

        doc = _retry_on_error(docs_service.documents().get, documentId=doc_id)
        doc_content = doc.get('body', {}).get('content', [])
        text = ""
        for elem in doc_content:
            if 'paragraph' in elem:
                for seg in elem['paragraph'].get('elements', []):
                    run = seg.get('textRun', {})
                    if 'content' in run:
                        text += run['content']

        return {
            "success": True,
            "result": {
                "document_id": doc_id,
                "title": doc.get('title', ''),
                "content": text.strip()
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("upload_to_drive", security_level=SecurityLevel.MEDIUM)
def upload_to_drive(args: Any) -> str:
    """Envia um arquivo local para o Google Drive."""
    args_dict = safe_parse_args(args)
    local_path = args_dict.get("local_path", args if isinstance(args, str) else "")
    drive_name = args_dict.get("drive_name", Path(local_path).name)

    if not Path(local_path).exists():
        return "Erro: Arquivo local não encontrado."

    try:
        creds = get_google_credentials()
        service = build('drive', 'v3', credentials=creds)
        media = MediaFileUpload(local_path, resumable=True)
        file = service.files().create(
            body={'name': drive_name}, media_body=media, fields='id'
        ).execute()
        return f"Upload OK. ID: {file.get('id')}"
    except Exception as e:
        return f"Falha no upload: {str(e)}"


@tool("google_calendar_add", security_level=SecurityLevel.SAFE, cloud_compatible=True)
def google_calendar_add(args: Any) -> Dict[str, Any]:
    """Adiciona evento ao Google Agenda. Requer 'summary', 'date' (YYYY-MM-DD) e 'time' (HH:MM)."""
    try:
        creds = get_google_credentials()
        service = build('calendar', 'v3', credentials=creds)

        args_dict = safe_parse_args(args)
        summary = args_dict.get("summary") or args_dict.get("title") or args_dict.get("description", "")
        date = args_dict.get("date")
        time_input = args_dict.get("time", "09:00")
        description = args_dict.get("description", "Adicionado pelo Koda")

        if not summary or not date:
            return {"success": False, "error": "'summary' e 'date' são obrigatórios."}

        if time_input and len(time_input.split(':')) >= 2:
            parts = time_input.split(':')
            time_input = f"{int(parts[0]):02d}:{int(parts[1]):02d}"

        start_dt = f"{date}T{time_input}:00"
        try:
            dt = datetime.datetime.fromisoformat(start_dt)
            end_dt = (dt + datetime.timedelta(hours=1)).isoformat()
        except Exception:
            try:
                h = int(time_input.split(':')[0]) + 1
                end_dt = f"{date}T{h:02d}:{time_input.split(':')[1]}:00" if h < 24 else f"{date}T23:59:59"
            except Exception:
                end_dt = f"{date}T23:59:59"

        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_dt, 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': end_dt, 'timeZone': 'America/Sao_Paulo'},
        }

        created = _retry_on_error(
            lambda: service.events().insert(calendarId='primary', body=event).execute()
        )
        return {
            "success": True,
            "result": {
                "event_id": created.get("id"),
                "link": created.get("htmlLink"),
                "status": f"'{summary}' agendado!"
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("google_calendar_list", security_level=SecurityLevel.SAFE, cloud_compatible=True)
def google_calendar_list(args: Any = None) -> Dict[str, Any]:
    """Lista compromissos do Google Agenda. Opcional: 'max_results' (padrão 10) e 'date' (YYYY-MM-DD) para filtrar por data."""
    try:
        creds = get_google_credentials()
        service = build('calendar', 'v3', credentials=creds)

        args_dict = safe_parse_args(args) if args else {}
        max_results = args_dict.get("max_results", 10)
        filter_date = args_dict.get("date")

        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = _retry_on_error(
            lambda: service.events().list(
                calendarId='primary', timeMin=now,
                maxResults=max_results, singleEvents=True,
                orderBy='startTime'
            ).execute()
        )
        events = events_result.get('items', [])

        if filter_date:
            events = [e for e in events if filter_date in (e['start'].get('dateTime', e['start'].get('date', '')))]

        if not events:
            return {"success": True, "result": "Nenhum evento encontrado."}

        lines = []
        for ev in events:
            start = ev['start'].get('dateTime', ev['start'].get('date'))
            lines.append(f"- [{ev.get('id')}] {start} - {ev.get('summary')}")

        return {"success": True, "result": "\n".join(lines)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("google_calendar_remove", security_level=SecurityLevel.MEDIUM, cloud_compatible=True)
def google_calendar_remove(args: Any) -> Dict[str, Any]:
    """Remove eventos específicos do Google Agenda. Aceita:
    - 'event_id': remove evento por ID exato
    - 'summary': remove eventos cujo título contenha este texto
    - 'date': remove eventos nesta data (YYYY-MM-DD)
    - 'all_future': true para remover TODOS os eventos futuros"""
    try:
        creds = get_google_credentials()
        service = build('calendar', 'v3', credentials=creds)
        args_dict = safe_parse_args(args)

        event_id = args_dict.get("event_id")
        summary_filter = args_dict.get("summary")
        date_filter = args_dict.get("date")
        all_future = args_dict.get("all_future", False)

        if event_id:
            _retry_on_error(
                lambda: service.events().delete(calendarId='primary', eventId=event_id).execute()
            )
            return {"success": True, "result": f"Evento {event_id} removido."}

        if not summary_filter and not date_filter and not all_future:
            return {"success": False, "error": "Informe event_id, summary, date ou all_future=true."}

        now = datetime.datetime.utcnow().isoformat() + 'Z'
        max_results = 50 if all_future else 20
        events = _retry_on_error(
            lambda: service.events().list(
                calendarId='primary', timeMin=now if not date_filter else None,
                timeMax=f"{date_filter}T23:59:59Z" if date_filter else None,
                maxResults=max_results, singleEvents=True
            ).execute()
        ).get('items', [])

        if date_filter:
            events = [e for e in events if date_filter in (e['start'].get('dateTime', e['start'].get('date', '')))]
        if summary_filter:
            sf = summary_filter.lower()
            events = [e for e in events if sf in e.get('summary', '').lower()]

        if not events:
            return {"success": True, "result": "Nenhum evento correspondeu aos critérios."}

        count = 0
        removed = []
        for ev in events:
            _retry_on_error(
                lambda eid=ev['id']: service.events().delete(calendarId='primary', eventId=eid).execute()
            )
            count += 1
            removed.append(ev.get('summary', ev['id']))

        return {"success": True, "result": f"{count} evento(s) removido(s): {', '.join(removed[:5])}{'...' if count > 5 else ''}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("google_sheets", security_level=SecurityLevel.MEDIUM, cloud_compatible=True)
def google_sheets(args: Any) -> Dict[str, Any]:
    """Lê ou escreve em Google Sheets. Parâmetros:
    'spreadsheet_id' (obrigatório), 'range' (ex: 'A1:C10'),
    'values' (lista de listas, para escrita), 'mode' ('read' ou 'write', padrão 'read')."""
    try:
        creds = get_google_credentials()
        service = build('sheets', 'v4', credentials=creds)
        args_dict = safe_parse_args(args)

        sheet_id = args_dict.get("spreadsheet_id") or args_dict.get("id") or args_dict.get("sheet_id")
        if not sheet_id:
            return {"success": False, "error": "'spreadsheet_id' é obrigatório."}

        sheet_range = args_dict.get("range", "A1:Z1000")
        mode = args_dict.get("mode", "read")
        values = args_dict.get("values")

        if mode == "write":
            if not values:
                return {"success": False, "error": "'values' é obrigatório para escrita (lista de listas)."}
            body = {"values": values}
            result = _retry_on_error(
                lambda: service.spreadsheets().values().update(
                    spreadsheetId=sheet_id, range=sheet_range,
                    valueInputOption="USER_ENTERED", body=body
                ).execute()
            )
            return {"success": True, "result": f"Planilha atualizada. {result.get('updatedCells', 0)} células afetadas."}
        else:
            result = _retry_on_error(
                lambda: service.spreadsheets().values().get(
                    spreadsheetId=sheet_id, range=sheet_range
                ).execute()
            )
            rows = result.get('values', [])
            if not rows:
                return {"success": True, "result": "Planilha vazia no range informado."}
            return {"success": True, "result": {"rows": len(rows), "data": rows[:50]}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("gmail_search", security_level=SecurityLevel.MEDIUM, cloud_compatible=True)
def gmail_search(args: Any) -> Dict[str, Any]:
    """Pesquisa emails no Gmail. Parâmetros:
    'query' (ex: 'from:joao after:2024/01/01'), 'max_results' (padrão 10)."""
    try:
        creds = get_google_credentials()
        service = build('gmail', 'v1', credentials=creds)
        args_dict = safe_parse_args(args)

        query = args_dict.get("query", "")
        max_results = args_dict.get("max_results", 10)

        result = _retry_on_error(
            lambda: service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
        )
        messages = result.get('messages', [])
        if not messages:
            return {"success": True, "result": "Nenhum email encontrado."}

        details = []
        for msg in messages[:max_results]:
            meta = _retry_on_error(
                lambda mid=msg['id']: service.users().messages().get(
                    userId='me', id=mid, format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
            )
            headers = {h['name']: h['value'] for h in meta.get('payload', {}).get('headers', [])}
            details.append({
                "id": msg['id'],
                "from": headers.get('From', '?'),
                "subject": headers.get('Subject', '(sem assunto)'),
                "date": headers.get('Date', '?')
            })

        return {"success": True, "result": {"total": len(messages), "emails": details}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("gmail_send", security_level=SecurityLevel.MEDIUM, cloud_compatible=True)
def gmail_send(args: Any) -> Dict[str, Any]:
    """Envia email via Gmail. Parâmetros: 'to', 'subject', 'body'."""
    try:
        creds = get_google_credentials()
        service = build('gmail', 'v1', credentials=creds)
        args_dict = safe_parse_args(args)

        to = args_dict.get("to", "")
        subject = args_dict.get("subject", "")
        body = args_dict.get("body", "")

        if not to or not subject:
            return {"success": False, "error": "'to' e 'subject' são obrigatórios."}

        message_text = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}"
        encoded = base64.urlsafe_b64encode(message_text.encode('utf-8')).decode('utf-8')

        _retry_on_error(
            lambda: service.users().messages().send(
                userId='me', body={'raw': encoded}
            ).execute()
        )
        return {"success": True, "result": f"Email enviado para {to}."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("youtube_search", security_level=SecurityLevel.SAFE, cloud_compatible=True)
def youtube_search(args: Any) -> Dict[str, Any]:
    """Pesquisa vídeos no YouTube. Parâmetros: 'query' (obrigatório), 'max_results' (padrão 5)."""
    try:
        creds = get_google_credentials()
        service = build('youtube', 'v3', credentials=creds)
        args_dict = safe_parse_args(args)

        query = args_dict.get("query", "")
        max_results = args_dict.get("max_results", 5)

        if not query:
            return {"success": False, "error": "'query' é obrigatório."}

        result = _retry_on_error(
            lambda: service.search().list(
                q=query, part='snippet', type='video',
                maxResults=max_results
            ).execute()
        )
        items = result.get('items', [])
        if not items:
            return {"success": True, "result": "Nenhum vídeo encontrado."}

        videos = []
        for item in items:
            vid = item['id']['videoId']
            snippet = item['snippet']
            videos.append({
                "title": snippet['title'],
                "video_id": vid,
                "url": f"https://youtube.com/watch?v={vid}",
                "channel": snippet['channelTitle'],
                "published": snippet['publishedAt']
            })

        return {"success": True, "result": videos}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("google_contacts", security_level=SecurityLevel.SAFE, cloud_compatible=True)
def google_contacts(args: Any) -> Dict[str, Any]:
    """Lista ou busca contatos do Google. Parâmetros: 'query' (opcional, para buscar)."""
    try:
        creds = get_google_credentials()
        service = build('people', 'v1', credentials=creds)
        args_dict = safe_parse_args(args) if args else {}

        query = args_dict.get("query")

        if query:
            result = _retry_on_error(
                lambda: service.people().searchContacts(
                    query=query, pageSize=10,
                    readMask='names,emailAddresses,phoneNumbers'
                ).execute()
            )
            people = result.get('results', [])
        else:
            result = _retry_on_error(
                lambda: service.people().connections().list(
                    resourceName='people/me', pageSize=10,
                    personFields='names,emailAddresses,phoneNumbers'
                ).execute()
            )
            people = result.get('connections', [])

        if not people:
            return {"success": True, "result": "Nenhum contato encontrado."}

        contacts = []
        for p in people:
            person = p.get('person', p)
            name = person.get('names', [{}])[0].get('displayName', '?') if person.get('names') else '?'
            email = person.get('emailAddresses', [{}])[0].get('value', '') if person.get('emailAddresses') else ''
            phone = person.get('phoneNumbers', [{}])[0].get('value', '') if person.get('phoneNumbers') else ''
            contacts.append({"name": name, "email": email, "phone": phone})

        return {"success": True, "result": contacts}
    except Exception as e:
        return {"success": False, "error": str(e)}
