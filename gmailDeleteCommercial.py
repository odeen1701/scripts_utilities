import imaplib
import re
import email
import sys
from bs4 import BeautifulSoup
from cred import USERNAME, PASSWORD, PROVIDER  # PROVIDER = 'icloud' o 'gmail'


# ─────────────────────────────────────────────
# Helpers robustos para respuestas IMAP
# ─────────────────────────────────────────────

def get_raw_email(msg_data):
    """Extrae el contenido bytes del email independientemente del servidor."""
    for part in msg_data:
        if isinstance(part, tuple) and len(part) >= 2 and isinstance(part[1], bytes):
            return part[1]
    return None


def safe_decode_flag(flag_data):
    """Decodifica flags IMAP de forma segura (iCloud devuelve ints a veces)."""
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
    """Decodifica el payload de un email probando varios encodings."""
    if payload is None:
        return ''
    for encoding in ('utf-8', 'iso-8859-1', 'windows-1252'):
        try:
            return payload.decode(encoding)
        except (UnicodeDecodeError, AttributeError):
            continue
    return ''

def move_to_trash(mail, email_id, trash_folder):
    """Mueve un correo a la papelera de forma compatible con iCloud y Gmail."""
    folder = f'"{trash_folder}"' if ' ' in trash_folder else trash_folder
    # Intentar MOVE (más limpio, soportado por iCloud y Gmail)
    try:
        result = mail._simple_command('MOVE', email_id.decode(), folder)
        if result[0] == 'OK':
            return True
    except Exception:
        pass
    # Fallback: COPY + DELETE
    try:
        status, _ = mail.copy(email_id, folder)
        if status == 'OK':
            mail.store(email_id, '+FLAGS', '\\Deleted')
            return True
    except Exception:
        pass
    return False
    return False

# ─────────────────────────────────────────────
# Configuración del servidor según proveedor
# ─────────────────────────────────────────────

IMAP_SERVERS = {
    'gmail':  'imap.gmail.com',
    'icloud': 'imap.mail.me.com',
}

TRASH_FOLDERS = {
    'gmail':  '[Gmail]/Trash',
    'icloud': 'Deleted Messages',
}

if PROVIDER not in IMAP_SERVERS:
    print(f"PROVIDER '{PROVIDER}' no reconocido. Usa 'gmail' o 'icloud' en cred.py")
    sys.exit(1)

IMAP_SERVER  = IMAP_SERVERS[PROVIDER]
TRASH_FOLDER = TRASH_FOLDERS[PROVIDER]


# ─────────────────────────────────────────────
# Menú de búsqueda
# ─────────────────────────────────────────────

def build_search_criteria():
    print("\n=== Email Search Options ===\n")
    criteria = []

    print("1. Status filter:")
    print("   1. Unread only (default)")
    print("   2. Read only")
    print("   3. All emails")
    print("   4. Flagged/Starred")
    print("   5. Answered")
    print("   6. Unanswered")
    status_choice = input("\nChoose status filter [1]: ").strip() or '1'
    status_map = {
        '1': 'UNSEEN', '2': 'SEEN', '3': 'ALL',
        '4': 'FLAGGED', '5': 'ANSWERED', '6': 'UNANSWERED'
    }
    criteria.append(status_map.get(status_choice, 'UNSEEN'))

    print("\n2. Date filter:")
    print("   1. No date filter (default)")
    print("   2. Since a date")
    print("   3. Before a date")
    print("   4. On a specific date")
    date_choice = input("\nChoose date filter [1]: ").strip() or '1'
    if date_choice in ('2', '3', '4'):
        date_value = input("   Enter date (DD-Mon-YYYY, e.g. 01-Jan-2024): ").strip()
        date_map = {'2': 'SINCE', '3': 'BEFORE', '4': 'ON'}
        criteria.append(f'{date_map[date_choice]} {date_value}')

    print("\n3. Sender filter:")
    from_value = input("   Filter by sender email (leave empty to skip): ").strip()
    if from_value:
        criteria.append(f'FROM "{from_value}"')

    print("\n4. Subject filter:")
    subject_value = input("   Filter by subject text (leave empty to skip): ").strip()
    if subject_value:
        criteria.append(f'SUBJECT "{subject_value}"')

    print("\n5. Body filter:")
    body_value = input("   Filter by body text (leave empty to skip): ").strip()
    if body_value:
        criteria.append(f'BODY "{body_value}"')

    print("\n6. Size filter:")
    print("   1. No size filter (default)")
    print("   2. Larger than (bytes)")
    print("   3. Smaller than (bytes)")
    size_choice = input("\nChoose size filter [1]: ").strip() or '1'
    if size_choice in ('2', '3'):
        size_value = input("   Enter size in bytes: ").strip()
        size_map = {'2': 'LARGER', '3': 'SMALLER'}
        criteria.append(f'{size_map[size_choice]} {size_value}')

    search_criteria = ' '.join(criteria)
    print(f"\n>>> Searching with criteria: {search_criteria}\n")
    return search_criteria


# ─────────────────────────────────────────────
# Patrones de suscripción / spam comercial
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
    r'si quieres dejar de recibir',
    r'si no quieres recibir más comunicaciones',
    r'si no quiere recibir más comunicaciones',
    r'si prefieres no recibir', r'modificar la suscripción',
    r'cambiar mis preferencias', r'preferences',
    r'recibir menos correos', r'ajustar mis preferencias'
]

regex_unificado = re.compile('|'.join(patrones), re.IGNORECASE)


# ─────────────────────────────────────────────
# Main
# ──────────────────────────��──────────────────

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
    print(f"Total mensajes encontrados: {len(email_ids)}")
    email_ids.reverse()

    for email_id in email_ids:

        # 1. Guardar flags actuales ANTES de leer (para no marcar como leído)
        status, flag_data = mail.fetch(email_id, '(FLAGS)')
        previous_flags = safe_decode_flag(flag_data)

        # 2. ✅ BODY.PEEK[] en lugar de RFC822 — no marca como leído, compatible iCloud
        status, msg_data = mail.fetch(email_id, '(BODY.PEEK[])')
        raw_email = get_raw_email(msg_data)  # ✅ compatible iCloud + Gmail

        if raw_email is None:
            print(f"⚠️  No se pudo leer el correo {email_id}, saltando...")
            continue

        msg = email.message_from_bytes(raw_email)

        # 3. Extraer contenido HTML
        html_content = ''
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    html_content = decode_payload(part.get_payload(decode=True))
                    break
        else:
            html_content = decode_payload(msg.get_payload(decode=True))

        # 4. Obtener texto plano del HTML
        body_text = ''
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            body_text = soup.get_text()
        else:
            print(f"ℹ️  Correo {email_id} sin contenido HTML.")

        # 5. Decidir qué hacer con el correo
        if body_text and regex_unificado.search(body_text):
            if move_to_trash(mail, email_id, TRASH_FOLDER):
                print(f'🗑️  Correo {email_id.decode()} movido a papelera ({TRASH_FOLDER}).')
            else:
                print(f'❌ No se pudo mover el correo {email_id.decode()}')
        else:
            # Restaurar estado no-leído si lo abrimos sin querer
            status, flag_data = mail.fetch(email_id, '(FLAGS)')
            current_flags = safe_decode_flag(flag_data)

            if '\\Seen' in current_flags and '\\Seen' not in previous_flags:
                mail.store(email_id, '-FLAGS', '\\Seen')
                print(f'📧 Correo {email_id} restaurado a no leído.')
            else:
                print(f'✅ Correo {email_id} ya estaba sin leer, omitiendo.')

    mail.expunge()
    print('\n✅ Proceso completado.')

except Exception as e:
    import traceback
    traceback.print_exc()

finally:
    mail.logout()
