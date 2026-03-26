import imaplib
import re
import email
import sys
from bs4 import BeautifulSoup
from cred import USERNAME, PASSWORD  #import credentials from cred.py file



def build_search_criteria():
    print("\n=== Email Search Options ===\n")

    criteria = []

    # 1. Status filter
    print("1. Status filter:")
    print("   1. Unread only (default)")
    print("   2. Read only")
    print("   3. All emails")
    print("   4. Flagged/Starred")
    print("   5. Answered")
    print("   6. Unanswered")
    status_choice = input("\nChoose status filter [1]: ").strip() or '1'
    status_map = {
        '1': 'UNSEEN',
        '2': 'SEEN',
        '3': 'ALL',
        '4': 'FLAGGED',
        '5': 'ANSWERED',
        '6': 'UNANSWERED'
    }
    criteria.append(status_map.get(status_choice, 'UNSEEN'))

    # 2. Date filter
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

    # 3. Sender filter
    print("\n3. Sender filter:")
    from_value = input("   Filter by sender email (leave empty to skip): ").strip()
    if from_value:
        criteria.append(f'FROM "{from_value}"')

    # 4. Subject filter
    print("\n4. Subject filter:")
    subject_value = input("   Filter by subject text (leave empty to skip): ").strip()
    if subject_value:
        criteria.append(f'SUBJECT "{subject_value}"')

    # 5. Body filter
    print("\n5. Body filter:")
    body_value = input("   Filter by body text (leave empty to skip): ").strip()
    if body_value:
        criteria.append(f'BODY "{body_value}"')

    # 6. Size filter
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



# Conectar al servidor IMAP de Gmail
mail = imaplib.IMAP4_SSL('imap.gmail.com')

patrones = [
        r'darte de baja',
        r'darme de baja',
        r'deja de recibir',
        r'si has dejado de estar interesado en recibir comunicaciones telemáticas',
        r'cancelar tu suscripción',
        r'cancela tu suscripción',
        r'if you do not want to receive these emails',
        r'si no desea seguir recibiendo',
        r'si no deseas recibir',
        r'se désinscrire',
        r'manage your email preferences',
        r'si no puedes ver correctamente este email',
        r'having trouble seeing this email?',
        r'darse de baja',
        r'gestionar tu suscripción',
        r'newsletter',
        r'suscripción',
        r'cancelar suscripción',
        r'unsubscribe',
        r'cancel subscription',
        r'dándote de baja',
        r'dejar de recibir',
        r'no desea recibir',
        r'no quiero recibir',
        r'manage your email preferences',
        r'desuscribirse',
        r'cancelar su suscripción',
        r'no quiero recibir más correos',
        r'opt-out',
        r'modificar tus preferencias',
        r'actualizar tus preferencias',
        r'si ya no deseas recibir',
        r'si no quieres recibir',
        r'retirar mi consentimiento',
        r'remover de la lista',
        r'si quieres dejar de recibir',
        r'si no quieres recibir más comunicaciones',
        r'si prefieres no recibir',
        r'modificar la suscripción',
        r'cambiar mis preferencias',
        r'preferences',
        r'recibir menos correos',
        r'ajustar mis preferencias'
]
try:


    search_criteria = build_search_criteria()

    # Iniciar sesión
    mail.login(USERNAME, PASSWORD)

    # Seleccionar la bandeja de entrada
    mail.select('inbox')

    # Buscar todos los correos en la bandeja de entrada
    status, messages = mail.search(None, search_criteria)

    if status == 'OK':
        # Obtener la lista de IDs de los mensajes
        email_ids = messages[0].split()
        print(f"total mensajes {len(email_ids)}")

        email_ids.reverse()

        for email_id in email_ids:
            # Fetch the email by ID
            status, flag_data = mail.fetch(email_id, '(FLAGS)')

            flags = flag_data[0].decode() if flag_data[0] else ''
            #Skip already-read emails
            if '\\Seen' in flags:
                print(f'{email_id} ya fue leído, omitiendo')
                continue

            # Only NOW fetch the full email (it was unread)
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])

            # Si el mensaje es multipart, obtener el contenido HTML
            # Obtener el contenido HTML
            html_content = ''  # Inicializa html_content como vacío

            if msg.is_multipart():
                found_html = False  # Bandera para verificar si se encontró contenido HTML
                for part in msg.walk():
                    if part.get_content_type() == 'text/html':
                        found_html = True  # Se encontró contenido HTML
                        payload = part.get_payload(decode=True)
                        if payload is not None:  # Verificar que payload no sea None
                            try:
                                html_content = payload.decode('utf-8')
                            except UnicodeDecodeError:
                                try:
                                    html_content = payload.decode('iso-8859-1')
                                except UnicodeDecodeError:
                                    html_content = ''  # Asignar vacío si no se puede decodificar
                        break  # Salir del bucle una vez que se encontró el contenido HTML
                if not found_html:
                    print("No se encontró contenido HTML en el mensaje.")
            else:
                payload = msg.get_payload(decode=True)
                if payload is not None:  # Verificar que payload no sea None
                    try:
                        html_content = payload.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            html_content = payload.decode('iso-8859-1')
                        except UnicodeDecodeError:
                            html_content = ''  # Asignar vacío si no se puede decodificar
                else:
                    print("El mensaje no tiene contenido.")

            # En este punto, html_content debe estar definido.
            # Puedes proceder a analizarlo con BeautifulSoup si no está vacío.
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
                body_text = soup.get_text()
                # Resto de tu código para procesar el texto...
            else:
                print("No hay contenido HTML para analizar.")

            # Verificar si la palabra "unsubscribe" está en el contenido
            regex_unificado = re.compile('|'.join(patrones), re.IGNORECASE)
            if (bool(regex_unificado.search(body_text))):
                # Mover el mensaje a la papelera (Trash)
                mail.copy(email_id, 'Trash')  # Copiar el correo a la papelera
                mail.store(email_id, '+FLAGS', '\\Deleted')  # Marcar el correo como eliminado en la bandeja de entrada
                print(f'Correo ID {email_id.decode()} movido a la papelera.')
            else:
                # Only mark as unread if the email was already read
                status, flag_data = mail.fetch(email_id, '(FLAGS)')
                flags = flag_data[0].decode() if flag_data[0] else ''

                if '\\Seen' in flags:
                    mail.store(email_id, '-FLAGS', '\\Seen')  # Mark as unread
                    print(f'{email_id} marcado como no leído')
                else:
                    print(f'{email_id} ya estaba sin leer, omitiendo')

        # Eliminar los correos marcados como eliminados
        mail.expunge()

        print('Proceso completado.')

    else:
        print('No se pudieron buscar los mensajes.')

except Exception as e:
    print(f'Error: {e}')

finally:
    # Cerrar la conexión
    mail.logout()
