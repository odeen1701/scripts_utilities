import imaplib
import sys
from cred import USERNAME, PASSWORD, PROVIDER


# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────

IMAP_SERVERS = {
    'gmail':  'imap.gmail.com',
    'icloud': 'imap.mail.me.com',
}

if PROVIDER not in IMAP_SERVERS:
    print(f"PROVIDER '{PROVIDER}' no reconocido. Usa 'gmail' o 'icloud' en cred.py")
    sys.exit(1)

IMAP_SERVER = IMAP_SERVERS[PROVIDER]


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

mail = imaplib.IMAP4_SSL(IMAP_SERVER)

try:
    mail.login(USERNAME, PASSWORD)
    mail.select('inbox')

    status, messages = mail.search(None, 'UNSEEN')

    if status != 'OK':
        print('No se pudieron buscar los mensajes.')
        sys.exit(1)

    email_ids = messages[0].split()
    total = len(email_ids)
    print(f"Mensajes sin leer: {total}")

    if total == 0:
        print("No hay mensajes sin leer.")
        sys.exit(0)

    # ✅ Marcar todos en un solo comando batch (1 llamada en lugar de N)
    batch_str = ','.join(id.decode() for id in email_ids)
    mail.store(batch_str, '+FLAGS', '\\Seen')

    print(f"✅ {total} mensajes marcados como leídos.")

except Exception as e:
    import traceback
    traceback.print_exc()

finally:
    mail.logout()
