import imaplib
import re
import email
import sys
import argparse
import cred
from bs4 import BeautifulSoup



# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def get_raw_email(msg_data):
    for part in msg_data:
        if isinstance(part, tuple) and len(part) >= 2 and isinstance(part[1], bytes):
            return part[1]
    return None


def safe_decode_flag(flag_data):
    if not flag_data:
        return ''
    for part in flag_data:
        if isinstance(part, tuple):
            for elem in part:
                if isinstance(elem, bytes):
                    return elem.decode()
        elif isinstance(part, bytes):
            return part.decode()
    return ''


def decode_payload(payload):
    if payload is None:
        return ''
    for encoding in ('utf-8', 'iso-8859-1', 'windows-1252'):
        try:
            return payload.decode(encoding)
        except (UnicodeDecodeError, AttributeError):
            continue
    return ''


def move_to_trash(mail, email_id, trash_folder):
    folder = f'"{trash_folder}"' if ' ' in trash_folder else trash_folder
    try:
        result = mail._simple_command('MOVE', email_id.decode(), folder)
        if result[0] == 'OK':
            return True
    except Exception:
        pass
    try:
        status, _ = mail.copy(email_id, folder)
        if status == 'OK':
            mail.store(email_id, '+FLAGS', '\\Deleted')
            return True
    except Exception:
        pass
    return False


def get_body_text(msg):
    """Extrae texto plano del mensaje (HTML preferido, fallback a text/plain)."""
    html_content = ''
    plain_content = ''

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/html' and not html_content:
                html_content = decode_payload(part.get_payload(decode=True))
            elif ct == 'text/plain' and not plain_content:
                plain_content = decode_payload(part.get_payload(decode=True))
    else:
        ct = msg.get_content_type()
        if ct == 'text/html':
            html_content = decode_payload(msg.get_payload(decode=True))
        else:
            plain_content = decode_payload(msg.get_payload(decode=True))

    if html_content:
        # ✅ lxml es más rápido que html.parser
        try:
            soup = BeautifulSoup(html_content, 'lxml')
        except Exception:
            soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)

    return plain_content


# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────

USERNAME = ""
PASSWORD = ""

parser = argparse.ArgumentParser()
parser.add_argument("provider", choices=["gmail", "icloud"])
args = parser.parse_args()
PROVIDER = args.provider


if PROVIDER == 'gmail':
    USERNAME = cred.USERNAME_GMAIL
    PASSWORD = cred.PASSWORD_GMAIL
elif PROVIDER == 'icloud':
    USERNAME = cred.USERNAME_ICLOUD
    PASSWORD = cred.PASSWORD_ICLOUD
else:
    raise ValueError(f"Provider not supported: {cred.PROVIDER}")

IMAP_SERVERS  = {'gmail': 'imap.gmail.com',        'icloud': 'imap.mail.me.com'}
TRASH_FOLDERS = {'gmail': '[Gmail]/Trash',          'icloud': 'Deleted Messages'}

if PROVIDER not in IMAP_SERVERS:
    print(f"PROVIDER '{creed.PROVIDER}' no reconocido. Usa 'gmail' o 'icloud' en cred.py")
    sys.exit(1)

IMAP_SERVER  = IMAP_SERVERS[PROVIDER]
TRASH_FOLDER = TRASH_FOLDERS[PROVIDER]


# ─────────────────────────────────────────────
# Menú de búsqueda
# ─────────────────────────────────────────────

def build_search_criteria():
    print(f"\n=== Email Search Options for provider {PROVIDER} ===\n")
    criteria = []

    print("1. Status filter:")
    print("   1. Unread only (default)  2. Read only  3. All  4. Flagged  5. Answered  6. Unanswered")
    status_map = {'1':'UNSEEN','2':'SEEN','3':'ALL','4':'FLAGGED','5':'ANSWERED','6':'UNANSWERED'}
    criteria.append(status_map.get(input("\nChoose [1]: ").strip() or '1', 'UNSEEN'))

    print("\n2. Date filter:  1. None (default)  2. Since  3. Before  4. On")
    date_choice = input("\nChoose [1]: ").strip() or '1'
    if date_choice in ('2', '3', '4'):
        date_value = input("   Date (DD-Mon-YYYY as in 11-May-2025): ").strip()
        date_map = {'2': 'SINCE', '3': 'BEFORE', '4': 'ON'}
        criteria.append(f'{date_map[date_choice]} {date_value}')

    from_value = input("\n3. Sender filter (empty to skip): ").strip()
    if from_value:
        criteria.append(f'FROM "{from_value}"')

    subject_value = input("\n4. Subject filter (empty to skip): ").strip()
    if subject_value:
        criteria.append(f'SUBJECT "{subject_value}"')

    body_value = input("\n5. Body filter (empty to skip): ").strip()
    if body_value:
        criteria.append(f'BODY "{body_value}"')

    print("\n6. Size filter:  1. None (default)  2. Larger than  3. Smaller than")
    size_choice = input("\nChoose [1]: ").strip() or '1'
    if size_choice in ('2', '3'):
        size_value = input("   Size in bytes: ").strip()
        criteria.append(f'{"LARGER" if size_choice=="2" else "SMALLER"} {size_value}')

    sc = ' '.join(criteria)
    print(f"\n>>> Criteria: {sc}\n")
    return sc


# ─────────────────────────────────────────────
# Patrones
# ─────────────────────────────────────────────

patrones = [
    r'darte de baja', r'darme de baja', r'deja de recibir',
    r'si has dejado de estar interesado en recibir comunicaciones telemáticas',
    r'cancelar tu suscripción', r'cancela tu suscripción',
    r'if you do not want to receive these emails',
    r'si no desea seguir recibiendo', r'si no deseas recibir',
    r'se désinscrire', r'manage your email preferences',
    r'si no puedes ver correctamente este email',
    r'having trouble seeing this email?', r'darse de baja',
    r'gestionar tu suscripción', r'newsletter', r'suscripción',
    r'cancelar suscripción', r'unsubscribe', r'cancel subscription',
    r'dándote de baja', r'dejar de recibir', r'no desea recibir',
    r'no quiero recibir', r'desuscribirse', r'cancelar su suscripción',
    r'no quiero recibir más correos', r'opt-out',
    r'modificar tus preferencias', r'actualizar tus preferencias',
    r'si ya no deseas recibir', r'si no quieres recibir',
    r'retirar mi consentimiento', r'remover de la lista',
    r'si quieres dejar de recibir', r'si no quieres recibir más comunicaciones',
    r'si no quiere recibir más comunicaciones', r'si prefieres no recibir',
    r'modificar la suscripción', r'cambiar mis preferencias', r'preferences',
    r'recibir menos correos', r'ajustar mis preferencias'
]

regex_unificado = re.compile('|'.join(patrones), re.IGNORECASE)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

mail = imaplib.IMAP4_SSL(IMAP_SERVER)

try:
    search_criteria = build_search_criteria()
    mail.login(USERNAME, PASSWORD)
    mail.select('inbox')

    status, messages = mail.search(None, search_criteria)
    if status != 'OK':
        print('No se pudieron buscar los mensajes.')
        sys.exit(1)

    email_ids = messages[0].split()
    total = len(email_ids)
    print(f"Total mensajes encontrados: {total}")
    email_ids.reverse()

    # ✅ OPTIMIZACIÓN 1: fetch FLAGS + BODY en una sola llamada por correo
    BATCH_SIZE = 50  # ✅ OPTIMIZACIÓN 2: procesar en lotes de 50
    to_delete  = []
    to_unseen  = []

    for i in range(0, total, BATCH_SIZE):
        batch = email_ids[i:i + BATCH_SIZE]

        # Un solo fetch por mensaje: FLAGS y BODY juntos
        batch_str = ','.join(id.decode() for id in batch)
        status, responses = mail.fetch(batch_str, '(FLAGS BODY.PEEK[])')

        # Reagrupar respuestas: cada email ocupa múltiples elementos en responses
        # Los separadores son bytes sueltos como b')' — agrupar por tuplas
        current_parts = []
        emails_parsed = []
        for part in responses:
            if isinstance(part, tuple):
                current_parts.append(part)
            elif isinstance(part, bytes) and part.strip() == b')':
                if current_parts:
                    emails_parsed.append(current_parts)
                    current_parts = []
        if current_parts:
            emails_parsed.append(current_parts)

        for idx, parts in enumerate(emails_parsed):
            email_id = batch[idx] if idx < len(batch) else None

            # Extraer FLAGS del header
            header_str = parts[0][0].decode() if isinstance(parts[0][0], bytes) else ''
            was_seen = '\\Seen' in header_str

            # Extraer body
            raw_email = None
            for part in parts:
                if isinstance(part, tuple) and len(part) >= 2 and isinstance(part[1], bytes):
                    raw_email = part[1]
                    break

            if raw_email is None:
                print(f"⚠️  No se pudo leer correo {email_id}, saltando...")
                continue

            msg       = email.message_from_bytes(raw_email)
            body_text = get_body_text(msg)

            if body_text and regex_unificado.search(body_text):
                to_delete.append(email_id)
            else:
                if not was_seen:
                    to_unseen.append(email_id)

        print(f"  Procesados {min(i + BATCH_SIZE, total)}/{total}...")

    # ✅ OPTIMIZACIÓN 3: operaciones de borrado/marcado en batch al final
    print(f"\n📊 Para borrar: {len(to_delete)} | Para mantener sin leer: {len(to_unseen)}")

    for email_id in to_delete:
        if move_to_trash(mail, email_id, TRASH_FOLDER):
            print(f'🗑️  {email_id.decode()} → papelera')
        else:
            print(f'❌  {email_id.decode()} no se pudo mover')

    # Marcar como no leídos en un solo comando batch
    if to_unseen:
        unseen_str = ','.join(id.decode() for id in to_unseen)
        mail.store(unseen_str, '-FLAGS', '\\Seen')
        print(f'📧 {len(to_unseen)} correos restaurados a no leído.')

    mail.expunge()
    print('\n✅ Proceso completado.')

except Exception as e:
    import traceback
    traceback.print_exc()

finally:
    mail.logout()
