import imaplib
import email
from cred import USERNAME,PASSWORD #need to define the credentias in a creed.py file.

# Conectar al servidor IMAP de Gmail
mail = imaplib.IMAP4_SSL('imap.gmail.com')

try:
    # Iniciar sesión
    mail.login(USERNAME, PASSWORD)

    # Seleccionar la bandeja de entrada
    mail.select('inbox')

    # Buscar todos los correos no leídos
    status, messages = mail.search(None, 'UNSEEN')

    if status == 'OK':
        # Obtener la lista de IDs de los mensajes no leídos
        email_ids = messages[0].split()
        print(f"numero de mensajes sin leer {len(email_ids)}")

        # Marcar cada mensaje como leído
        for email_id in email_ids:
            mail.store(email_id, '+FLAGS', '\\Seen')
            print(f"email {email_id} marcado como leido")

        print(f'Se han marcado como leídos {len(email_ids)} mensajes.')

    else:
        print('No se pudieron buscar los mensajes.')

except Exception as e:
    print(f'Error: {e}')

finally:
    # Cerrar la conexión
    mail.logout()
