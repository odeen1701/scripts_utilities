import imaplib  
import email  
from bs4 import BeautifulSoup  
from cred import USERNAME, PASSWORD  #import credentials from cred.py file  
  
# Conectar al servidor IMAP de Gmail  
mail = imaplib.IMAP4_SSL('imap.gmail.com')  
  
try:  
    # Iniciar sesión  
    mail.login(USERNAME, PASSWORD)  
  
    # Seleccionar la bandeja de entrada  
    mail.select('inbox')  
  
    # Buscar todos los correos en la bandeja de entrada  
    status, messages = mail.search(None, 'ALL')  
  
    if status == 'OK':  
        # Obtener la lista de IDs de los mensajes  
        email_ids = messages[0].split()  
        print(f"total mensajes {len(email_ids)}")
  
        for email_id in email_ids:  
            # Fetch the email by ID  
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
            if (  
                'unsubscribe' in body_text.lower() or  
                'darse de baja' in body_text.lower() or  
                'dejar de recibir' in body_text.lower() or
                'cancelar tu suscripción' in body_text.lower() or  
                'cancel subscription' in body_text.lower()  
            ):  
                # Mover el mensaje a la papelera (Trash)  
                mail.copy(email_id, 'Trash')  # Copiar el correo a la papelera  
                mail.store(email_id, '+FLAGS', '\\Deleted')  # Marcar el correo como eliminado en la bandeja de entrada  
                print(f'Correo ID {email_id.decode()} movido a la papelera.')  
  
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
